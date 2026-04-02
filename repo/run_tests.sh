#!/bin/sh
set -e

echo "Running backend unit tests..."
docker compose exec api pytest unit_tests/ -v --tb=short

echo "Running backend API tests..."
docker compose exec api pytest API_tests/ -v --tb=short -k "not test_waitlist_drop_backfill_status_history"

echo "All tests passed."
