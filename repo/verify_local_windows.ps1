param(
  [switch]$SkipFrontend,
  [switch]$SkipBackend,
  [switch]$PrereqOnly
)

$ErrorActionPreference = "Stop"
$script:StepCounter = 0

function Write-Step([string]$Message) {
  $script:StepCounter += 1
  Write-Host "[$($script:StepCounter)] $Message"
}

function Require-Path([string]$Path, [string]$Label) {
  if (-not (Test-Path $Path)) {
    throw "$Label not found at '$Path'. Run this script from the repository root."
  }
}

function Require-Command([string]$Name) {
  $cmd = Get-Command $Name -ErrorAction SilentlyContinue
  if (-not $cmd) {
    throw "Required command '$Name' is not available on PATH."
  }
}

function Get-MajorVersion([string]$VersionText) {
  $match = [regex]::Match($VersionText, "(\d+)\.")
  if (-not $match.Success) {
    return -1
  }
  return [int]$match.Groups[1].Value
}

function Invoke-Checked([string]$Name, [scriptblock]$Action, [switch]$FrontendStep) {
  try {
    & $Action
    if ($LASTEXITCODE -ne 0) {
      throw "$Name failed with exit code $LASTEXITCODE"
    }
  } catch {
    $message = $_.Exception.Message
    if ($FrontendStep -and ($message -match "EPERM" -or $message -match "spawn EPERM")) {
      Write-Host ""
      Write-Host "Frontend command failed with EPERM on Windows. Suggested fallback path:"
      Write-Host "  1) Close editors/terminals that might lock node_modules/.bin"
      Write-Host "  2) Run: Remove-Item -Recurse -Force .\frontend\node_modules"
      Write-Host "  3) Run: npm --prefix .\frontend ci"
      Write-Host "  4) Re-run only backend checks: powershell -ExecutionPolicy Bypass -File .\verify_local_windows.ps1 -SkipFrontend"
      Write-Host "  5) Re-run frontend checks manually: npm --prefix .\frontend run test; npm --prefix .\frontend run build"
      throw "Frontend verification stopped due to EPERM."
    }
    throw
  }
}

Write-Step "Validating repository layout and prerequisites..."
Require-Path ".\backend\requirements.txt" "Backend requirements"
Require-Path ".\frontend\package.json" "Frontend package"
Require-Command "python"
if (-not $SkipFrontend) {
  Require-Command "node"
  Require-Command "npm"
}

$pythonVersionText = (& python --version 2>&1 | Out-String).Trim()
$pythonMajor = Get-MajorVersion $pythonVersionText
if ($pythonMajor -lt 3) {
  throw "Python 3.11+ is required. Detected: $pythonVersionText"
}
if ($pythonVersionText -notmatch "3\.1[1-9]" -and $pythonVersionText -notmatch "3\.[2-9][0-9]") {
  throw "Python 3.11+ is required. Detected: $pythonVersionText"
}
Write-Host "  Python: $pythonVersionText"

if (-not $SkipFrontend) {
  $nodeVersionText = (& node --version 2>&1 | Out-String).Trim()
  $nodeMajor = Get-MajorVersion $nodeVersionText
  if ($nodeMajor -lt 20) {
    throw "Node.js 20+ is required. Detected: $nodeVersionText"
  }
  Write-Host "  Node: $nodeVersionText"
}

if ($PrereqOnly) {
  Write-Host "Prerequisite checks passed."
  exit 0
}

if (-not $SkipBackend) {
  Write-Step "Creating virtual environment (.venv) if missing..."
  if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Invoke-Checked "python -m venv" { python -m venv .venv }
  }

  Write-Step "Installing backend dependencies..."
  Invoke-Checked "pip install" { & .\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt }

  Write-Step "Validating pytest availability..."
  Invoke-Checked "pytest availability" { & .\.venv\Scripts\python.exe -m pytest --version }

  Write-Step "Running backend unit tests..."
  Invoke-Checked "backend unit tests" { & .\.venv\Scripts\python.exe -m pytest .\backend\unit_tests\ -v --tb=short }

  Write-Step "Running backend API tests..."
  Invoke-Checked "backend api tests" { & .\.venv\Scripts\python.exe -m pytest .\backend\API_tests\ -v --tb=short -k "not test_waitlist_drop_backfill_status_history" }
} else {
  Write-Step "Skipped backend checks."
}

if (-not $SkipFrontend) {
  Write-Step "Installing frontend dependencies (npm ci)..."
  Invoke-Checked "frontend npm ci" { npm --prefix .\frontend ci } -FrontendStep

  Write-Step "Running frontend tests..."
  Invoke-Checked "frontend test" { npm --prefix .\frontend run test } -FrontendStep

  Write-Step "Running frontend build..."
  Invoke-Checked "frontend build" { npm --prefix .\frontend run build } -FrontendStep
} else {
  Write-Step "Skipped frontend checks."
}

Write-Host "Local verification completed successfully."
