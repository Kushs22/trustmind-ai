"""
# Postgres backups (TrustMind AI)

Practical durability for the Render Postgres database used by the API.

This project does **not** invent a custom backup service. Durability relies on
Render’s Postgres features plus an optional local dump script for operators.

## What holds production data

| Store | Contents | Persistence |
|-------|----------|-------------|
| Render Postgres (`DATABASE_URL`) | `users`, `check_ins` (including `conversation_json`) | Durable across API redeploys |
| Ephemeral disk / temp dirs | Image & PDF bytes during preprocess | Deleted after the request |
| Client `localStorage` | JWT access token only | Not a data vault |

## Render Postgres backups (recommended)

1. Open the **Render Dashboard** → your Postgres instance (`trustmind-db` or
   equivalent).
2. Check the plan:
   - **Free / starter tiers** often have **limited or no automated point-in-time
     backups**. Treat free DB data as best-effort for a demo.
   - **Paid Postgres** typically enables **daily automated backups** and
     restore from the dashboard. Prefer this before treating the demo as
     “production-grade” durability.
3. Document who can restore (account owner / dissertation team) and keep the
   **External Database URL** only in password managers — never in git.
4. After a restore, re-check the web service `DATABASE_URL` still points at the
   restored instance and hit `GET /health`.

Official reference: [Render PostgreSQL docs](https://render.com/docs/databases)
(backup / restore sections for your current plan).

## Optional operator dump (local / CI secret)

Use when you need a one-off export (e.g. before a risky schema change). Requires
`pg_dump` and `DATABASE_URL` in the environment (External URL with SSL is usual
from a laptop).

```bash
# From repo root — never commit the output file
export DATABASE_URL='postgresql://USER:PASSWORD@HOST:5432/DB?sslmode=require'
chmod +x scripts/dump_postgres.sh
./scripts/dump_postgres.sh
# → writes backups/trustmind-YYYYMMDD-HHMMSS.sql (gitignored)
```

The script refuses to run without `DATABASE_URL` and never prints the password.

## What this does *not* cover

- Continuous WAL / PITR on free tiers
- Encrypted offsite replication we operate ourselves
- Backing up OpenAI/LLM provider logs (outside our control)

For a student public demo, Render paid backups + the dump script are the honest
bar. Upgrade Postgres before relying on history for real users.
