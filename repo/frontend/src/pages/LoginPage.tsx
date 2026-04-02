import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  Stack,
  TextField,
  Typography
} from "@mui/material";
import { useMemo, useState } from "react";

import { useAuth } from "../contexts/AuthContext";

type LoginPageProps = {
  onSuccess: () => void;
};

function validate(username: string, password: string) {
  return {
    username: username.trim() ? undefined : "Username is required.",
    password:
      !password ? "Password is required." : password.length < 12 ? "Password must be at least 12 characters." : undefined
  };
}

export function LoginPage({ onSuccess }: LoginPageProps) {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const errors = useMemo(() => validate(username, password), [username, password]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    if (errors.username || errors.password) {
      setError("Please fix the highlighted fields and try again.");
      return;
    }
    setIsSubmitting(true);
    try {
      await login(username.trim(), password);
      onSuccess();
    } catch (err) {
      const status =
        typeof err === "object" && err && "response" in err
          ? (err as { response?: { status?: number; data?: { detail?: string } } }).response?.status
          : undefined;
      const detail =
        typeof err === "object" && err && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      if (status === 423) {
        setError(detail ?? "Account is locked. Please wait before retrying.");
      } else if (status === 401) {
        setError("Invalid credentials.");
      } else {
        setError(detail ?? "Login failed. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", p: { xs: 2, md: 4 } }}>
      <Grid container spacing={3} sx={{ maxWidth: 1080 }}>
        <Grid size={{ xs: 12, md: 7 }}>
          <Card sx={{ height: "100%", borderRadius: 4, background: "linear-gradient(160deg, #0f4c5c 0%, #184f60 55%, #2f6672 100%)", color: "#f4f7f5" }}>
            <CardContent sx={{ p: { xs: 3, md: 5 } }}>
              <Stack spacing={2.5}>
                <Chip label="Air-gapped operations" size="small" sx={{ width: "fit-content", color: "#fff", backgroundColor: "rgba(255,255,255,0.22)" }} />
                <Typography variant="h3">CEMS Command Center</Typography>
                <Typography variant="body1" sx={{ color: "rgba(244,247,245,0.9)" }}>
                  Enrollment, scoring, finance, governance, and offline messaging in one resilient platform.
                </Typography>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 5 }}>
          <Card sx={{ borderRadius: 4 }}>
            <CardContent sx={{ p: { xs: 3, md: 4 } }}>
              <Stack component="form" spacing={2.25} noValidate onSubmit={handleSubmit}>
                <Typography variant="h4" color="primary.dark">
                  Sign In
                </Typography>
                <TextField label="Username" fullWidth value={username} onChange={(e) => setUsername(e.target.value)} error={Boolean(errors.username)} helperText={errors.username} />
                <TextField label="Password" type="password" fullWidth value={password} onChange={(e) => setPassword(e.target.value)} error={Boolean(errors.password)} helperText={errors.password ?? "Minimum 12 characters."} />
                {error && <Alert severity="error">{error}</Alert>}
                <Button type="submit" variant="contained" size="large" disabled={isSubmitting} startIcon={isSubmitting ? <CircularProgress color="inherit" size={16} /> : undefined}>
                  {isSubmitting ? "Signing in..." : "Sign In"}
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
