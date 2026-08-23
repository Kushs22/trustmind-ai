#!/usr/bin/env bash
# One-off Postgres dump for TrustMind operators.
# Requires: pg_dump on PATH, DATABASE_URL in the environment.
# Never commit dump files. Secrets must not be hardcoded here.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${TRUSTMIND_BACKUP_DIR:-$ROOT/backups}"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "error: set DATABASE_URL (Render External URL is typical from a laptop)." >&2
  echo "example: export DATABASE_URL='postgresql://user:pass@host:5432/db?sslmode=require'" >&2
  exit 1
fi

if ! command -v pg_dump >/dev/null 2>&1; then
  echo "error: pg_dump not found. Install PostgreSQL client tools." >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
OUT_FILE="$OUT_DIR/trustmind-${STAMP}.sql"

# pg_dump reads connection URI; do not echo DATABASE_URL.
pg_dump --no-owner --no-acl --format=plain --file="$OUT_FILE" "$DATABASE_URL"

echo "Wrote $OUT_FILE"
echo "Keep this file private; add backups/ to .gitignore if missing."
