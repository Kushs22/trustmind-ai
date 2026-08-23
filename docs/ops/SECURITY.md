# TrustMind AI — launch security checklist

Operator guide for Render (API) + Vercel (frontend). This is a student/dissertation public demo, not a clinical product — still apply the basics below before sharing the URL widely.

## Implemented in code

| Control | Where |
|--------|--------|
| Strong `SECRET_KEY` required on Render / production | `backend/app/config.py` (fails startup if weak) |
| CORS allowlist (no `*` in production) | `CORS_ORIGINS` + optional `FRONTEND_URL` |
| Rate limits: analyse, auth, chat, uploads, transcribe | `backend/app/services/rate_limit.py` |
| Password strength on register | Backend + frontend (`lib/password.ts`) |
| Account export / delete | `/privacy` + `/api/v1/privacy/*` |
| Security headers (HSTS, frame deny, CSP, …) | `frontend/next.config.ts` |
| LLM keys only on backend | Frontend exposes only `NEXT_PUBLIC_API_URL` |

## Manual steps (you must do these)

### 1. Render — secrets and env

In the **trustmind-api** web service → Environment:

1. **`SECRET_KEY`** — if blueprint `generateValue` was used, confirm it is present and long. Otherwise set:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

   Paste the value into Render. Never commit it. Rotate if it ever appears in logs/chat/git.

2. **`CORS_ORIGINS`** — comma-separated, no spaces preferred:

   ```text
   https://trustmind-ai.vercel.app
   ```

   Localhost is only for local API runs. For a **custom Vercel domain**, add it:

   ```text
   https://trustmind-ai.vercel.app,https://www.yourdomain.com
   ```

   Or set **`FRONTEND_URL=https://www.yourdomain.com`** (merged into the allowlist).

3. **`DATABASE_URL`** — use the Render Postgres **Internal** connection string (same region). Do not open the database to the public internet.

4. Provider keys (**backend only**): `OPENAI_API_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY` as needed.
   Default Groq model is `openai/gpt-oss-120b` (`GROQ_MODEL`). If you previously set
   `GROQ_MODEL=llama-3.3-70b-versatile` on Render, update or remove it (that model was
   retired Aug 2026).

5. Redeploy after env changes. Confirm `GET /health` and that login/analyse from the Vercel origin succeed (CORS errors in the browser console usually mean a missing origin).

### 2. Vercel — frontend env

| Variable | Value |
|----------|--------|
| `NEXT_PUBLIC_API_URL` | `https://trustmind-ai.onrender.com` (or your API custom domain) |

Do **not** add OpenAI/Groq/Gemini keys or `SECRET_KEY` to Vercel.

### 3. LLM spend caps (abuse mitigation)

Rate limits reduce runaway traffic; they do not replace billing caps.

- **OpenAI**: set a hard monthly budget / usage limits in the OpenAI usage dashboard; enable email alerts.
- **Groq**: set org limits / monitor usage in the Groq console.
- **Gemini (AI Studio)**: monitor quotas; treat free-tier keys as burnable and rotate if abused.

If the demo goes viral, temporarily disable paid providers (`LLM_PROVIDER=free` / remove paid keys) rather than leaving uncapped spend.

### 4. Postgres hygiene

- Prefer **Internal URL** on Render; keep External URL out of git and only in a password manager for laptop dumps.
- Use a strong DB password (Render generates one).
- Review backups: see [`BACKUPS.md`](./BACKUPS.md). Free/starter tiers may lack automated backups.

### 5. Rotate secrets after incidents

If a key leaks: rotate `SECRET_KEY` (invalidates existing JWTs), rotate LLM keys, and redeploy. Users will need to log in again.

## Rate limits (defaults)

Per client IP, per 60s window (override via env — see `backend/.env.example`):

| Action | Default |
|--------|---------|
| Analyse | 15 |
| Login | 5 |
| Register | 5 |
| Anonymous session | 10 |
| Chat follow-up (text/audio) | 20 |
| Image/PDF upload preprocess | 30 |
| Transcribe | 20 |

Exceeded requests return **HTTP 429** with a clear `detail` message (and `Retry-After` when known).

## Auth & privacy

- Register requires ≥8 characters, a letter, and a number or special character.
- Signed-in users can **export** or **delete** account data from the Privacy page.
- **Email verification** is intentionally **not** implemented for this demo phase (document only — next phase if the product leaves dissertation scope).

## Next phase (not implemented)

- Email verification / password reset flows
- Per-user (not only IP) rate limits with Redis
- Stricter CSP with nonces (remove `unsafe-inline` / `unsafe-eval`)
- WAF / bot protection in front of the API
- Antivirus scanning on uploads

## Quick verify after deploy

1. Visit the Vercel site → Analyse anonymously → follow-up chat works.
2. Sign up with a weak password (`password`) → rejected.
3. Hit login repeatedly → eventually 429.
4. Browser DevTools → Response headers include `X-Frame-Options: DENY` and CSP.
5. Confirm no LLM keys appear in the frontend bundle / Network → JS sources.
