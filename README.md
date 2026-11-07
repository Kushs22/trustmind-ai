# TrustMind AI

A **private, non-diagnostic wellbeing check-in** for anyone who needs support.  
Grounded in trusted UK guidance (NHS, Mind, Samaritans, CALM, Rethink), with **live Bristol community listings** from [Nyata AI](https://nyataai.co.uk).

The MSc dissertation compared a standalone LLM with the same model plus RAG. That evaluation stays under `research/`. The live product is a general tool.

---

## Live product

| Surface | URL |
|---------|-----|
| **Website (frontend)** | [https://trustmind-ai.vercel.app](https://trustmind-ai.vercel.app) |
| **Wellbeing check-in / analyse** | [https://trustmind-ai.vercel.app/analyse](https://trustmind-ai.vercel.app/analyse) |
| **Backend API** | [https://trustmind-ai.onrender.com](https://trustmind-ai.onrender.com) |
| **OpenAPI docs** | [https://trustmind-ai.onrender.com/docs](https://trustmind-ai.onrender.com/docs) |
| **Health / version** | [https://trustmind-ai.onrender.com/health](https://trustmind-ai.onrender.com/health) |
| **Source code** | [https://github.com/Kushs22/trustmind-ai](https://github.com/Kushs22/trustmind-ai) |

> **Keep-alive:** a sleeping host still causes a slow first request. Ping `GET /warmup` every 5–10 minutes (UptimeRobot, or the GitHub Action in `.github/workflows/keepalive.yml`). That is a stopgap. **True always-on needs a paid Render/Fly instance** (`min_machines_running = 1` / Starter plan). Do not claim the API is always warm until hosting is upgraded.

---

## What it does

1. User shares how they feel (**typed text**, optional **speech / image / PDF**). Anonymous is the default.
2. They can compare a **Quick check** (model only) with a **Grounded check** (approved sources).
3. Backend runs the model (hybrid **BM25 + FAISS + RRF** on the grounded path), then may query **Nyata** for Bristol listings. Nyata results are never cached.
4. Response includes:
   - non-diagnostic **research category** (e.g. Anxiety-related indicators)
   - **calibrated confidence** + **uncertainty**
   - **grounding status** (standalone / limited / grounded)
   - **trust signals** (model / evidence / retrieval — RAG only)
   - **reasoning** (non-diagnostic language)
   - **retrieved sources + evidence cards** (RAG only)
   - **crisis support links** when safety language appears
  - **local Bristol cards** from Nyata AI when the key is configured

Uploaded files are **user context only** — never written into the trusted RAG index.

This is **not** a diagnosis, therapy, or crisis intervention service.

### Nyata AI partnership

After the TrustMind assessment, the API can call `POST https://nyataai.co.uk/external_api.php` with `X-API-Key` (`NYATA_API_KEY`). Bristol is sent as `city` plus `location` `{latitude: 51.4545, longitude: -2.5879}`. Confirm the key with Ibrahim before production tests — credentials were deactivated 27 Oct 2026.

Nyata capability notes: OpenAI-style chat completions, text reply plus `nyata.results` listings. No documented streaming of the TrustMind verifier path. Do not stream unverified model text.

### Traffic

- Postgres: use a **connection pooler** (Supabase/Neon port 6543) and `DB_POOL_SIZE`.
- National RAG hits are TTL-cached (`RAG_CACHE_TTL_SECONDS=3600`). **Do not cache Nyata.**
- Frontend calls `/warmup` on load. Add an uptime ping as above.

---

## Research question

> To what extent does Retrieval-Augmented Generation (RAG) improve the **trustworthiness, reliability and explainability** of LLM-generated wellbeing assessments compared with a standalone LLM?

### Controlled evaluation (full synthetic test set, n=500, seed=42)

| Metric | LLM-only | LLM+RAG (BM25) | Δ (RAG − LLM) |
|--------|----------|----------------|---------------|
| Accuracy | **0.860** | **0.832** | **−0.028** |
| Macro-F1 | **0.863** | **0.835** | **−0.028** |
| Precision (macro) | 0.883 | 0.853 | −0.030 |
| Recall (macro) | 0.860 | 0.832 | −0.028 |

**Corpus:** `datasets/synthetic_wellbeing/` v2 (2,500 posts; eval on **all 500 test** rows).  
Earlier n=100 pilot: LLM 0.840 / RAG 0.830 (archived under `research/results/archive_n100_v2/`).  
**Interpretation:** larger n stabilises estimates; RAG still does **not** improve theme-label accuracy. Trust/explainability improve via allow-listed sources.  
Full write-up: [`research/results/rq_answer_summary.md`](research/results/rq_answer_summary.md).

---

## Architecture

```
Browser (Next.js · Vercel)  https://trustmind-ai.vercel.app
    │  optional: speech / image / PDF preprocess → user confirms text
    ▼
POST /api/v1/analyse  →  FastAPI (Render)  https://trustmind-ai.onrender.com
    │
    ├─ pipeline_mode=llm  →  model only (Quick check)
    └─ pipeline_mode=rag  →  BM25 + FAISS → RRF → grounded generation
    │
    ▼
Nyata AI (optional) → live Bristol listings (never cached)
    │
    ▼
Support resources if crisis language / high-risk category
```

| Layer | Stack |
|-------|--------|
| Frontend | Next.js, React, TypeScript, Tailwind · **Vercel** |
| Backend | FastAPI, Uvicorn, SQLAlchemy · **Render** |
| LLM | OpenAI **gpt-4.1** |
| Embeddings | **text-embedding-3-small** |
| Sparse retrieval | **BM25** (`rank_bm25`) |
| Dense retrieval | **FAISS** `IndexFlatIP` |
| Fusion | Reciprocal Rank Fusion (**k=60**) |
| Speech | Web Speech API / Whisper |
| Vision / PDF | GPT vision extract / pypdf |

API keys stay on the **server only**. The frontend never calls OpenAI.

---

## Repository map

```
trustmind-ai/
├── frontend/                 # Next.js app (Vercel)
├── backend/                  # FastAPI app (Render, rootDir=backend)
├── rag/                      # Hybrid retriever + RAG inference
├── knowledge_base/           # Allow-listed sources, chunks, indexes
├── research/                 # Experiments, metrics, figures, scripts
├── scripts/                  # Collect / chunk / embed / index builders
├── datasets/synthetic_wellbeing/  # Ethical eval CSVs (+ zip for download)
└── requirements-rag.txt
```

---

## Quick start (local)

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # set OPENAI_API_KEY, CORS_ORIGINS, etc.
uvicorn app.main:app --reload --port 8000
```

Docs: http://127.0.0.1:8000/docs · Health: http://127.0.0.1:8000/health

### 2. Frontend

```bash
cd frontend
npm install
# .env.local: NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
npm run dev
```

Open http://localhost:3000/analyse

### 3. (Optional) Rebuild RAG indexes

```bash
pip install -r requirements-rag.txt
export OPENAI_API_KEY=...
python scripts/chunk_documents.py --force
python scripts/generate_embeddings.py
python scripts/build_faiss.py
python scripts/build_bm25.py
```

Production indexes are committed under `knowledge_base/indexes/` so Render can run RAG without a rebuild step.

---

## LLM vs LLM+RAG (product)

| | **LLM** | **LLM+RAG** |
|--|---------|-------------|
| Retrieval | None | Hybrid BM25 + FAISS + RRF |
| Grounding label | Standalone model response | Grounded / Limited / … |
| Evidence & retrieval bars | Not applicable | 0–100 scores |
| Sources / evidence cards | Hidden | Shown from allow-list |
| Confidence formula | Self-report + consistency + input clarity | + retrieval similarity / agreement / coverage |

Per-request switch on the analyse UI (`pipeline_mode`: `llm` | `rag` | `auto`).  
Server default for `auto`: `USE_RAG` in `backend/.env` / Render env.

---

## Trust, safety, ethics

| Control | Behaviour |
|---------|-----------|
| Non-diagnostic UI | Display names like “Anxiety-related indicators” |
| Abstention | If calibrated confidence &lt; 0.75 (configurable) → no forced label |
| Grounding thresholds | Retrieval quality ≥ 55 and evidence ≥ 50 → fully grounded |
| Curated KB only | No free web crawl; `approved_sources.csv` allow-list |
| Uploads | Never enter FAISS/BM25; privacy mode default |
| Crisis support | Rule-based; independent of confidence / RAG success |
| Evaluation data | Synthetic wellbeing CSVs (`datasets/synthetic_wellbeing/`) — same label schema as SWMH, no scraped Reddit posts |

---

## Multimodal input

Typed text, speech, images, and PDFs → extract/confirm text → same analyse pipelines.

| Modality | Path |
|----------|------|
| Speech | Web Speech API or `POST /api/v1/transcribe` (Whisper) |
| Image | `POST /api/v1/process-image` (EXIF strip + vision extract) |
| PDF | `POST /api/v1/process-pdf` (pypdf; encrypted rejected) |

Limits and privacy details: see backend env in `backend/.env.example` and sections below in code comments.

---

## Evaluation scripts & artefacts

```bash
# Hybrid BM25+FAISS, temp=0.0 (needs OpenAI network from your machine)
python research/run_rag_vs_llm_eval.py

# Fair dual arm via local API proxy (BM25 retrieval)
python research/run_rag_vs_llm_via_local_api.py
```

| Artefact | Description |
|----------|-------------|
| `research/results/llm_baseline_metrics.json` | Notebook Arm A (temp=0.0) |
| `research/results/llm_proxy_metrics.json` | Fair LLM arm |
| `research/results/rag_metrics.json` | Fair RAG arm |
| `research/results/llm_vs_rag_comparison.csv` | Side-by-side deltas |
| `research/results/rq_answer_summary.md` | RQ + ethics |
| `research/figures/*_confusion_matrix.png` | Plots |

Row-level `*_predictions.csv` files are **gitignored** (contain raw Reddit evaluation text). Regenerate locally if needed.

---

## Backend tests

```bash
cd backend
python -m unittest tests.test_multimodal_input tests.test_trust_explainability tests.test_check_in_persistence -v
```

---

## Key environment variables

| Variable | Role |
|----------|------|
| `OPENAI_API_KEY` | Required for LLM / embeddings / multimodal |
| `OPENAI_MODEL` | Default `gpt-4.1` |
| `GROQ_API_KEY` | Optional free/fast provider (tried before Gemini/OpenAI in `auto`/`free`) |
| `GROQ_MODEL` | Default `openai/gpt-oss-120b` (`llama-3.3-70b-versatile` retired Aug 2026) |
| `USE_RAG` | Default for `pipeline_mode=auto` |
| `RAG_TOP_K` | Passages in RAG prompt (default 5) |
| `ENABLE_ABSTENTION` / `CONFIDENCE_THRESHOLD` | Fail-soft labelling |
| `ENABLE_CONFIDENCE_CALIBRATION` / `CONSISTENCY_RUNS` | Multi-run calibration |
| `CORS_ORIGINS` | Explicit allowlist (e.g. `https://trustmind-ai.vercel.app`); add custom domains; never `*` in production |
| `FRONTEND_URL` | Optional single extra origin merged into CORS |
| `SECRET_KEY` | Long random JWT secret (≥32 chars); required on Render |
| `DATABASE_URL` | **Postgres on Render** (required). Prefer Internal URL; SQLite is local-dev only |
| `NEXT_PUBLIC_API_URL` | Frontend → backend URL (only safe `NEXT_PUBLIC_*` var) |

See `backend/.env.example`, `backend/render.yaml`, `frontend/.env.local.example`, and the launch checklist [`docs/ops/SECURITY.md`](docs/ops/SECURITY.md).

---

## Deploy

| Target | Notes |
|--------|--------|
| **Frontend → Vercel** | Root `frontend/`; set `NEXT_PUBLIC_API_URL=https://trustmind-ai.onrender.com` |
| **Backend → Render** | `rootDir: backend`; `PYTHONPATH` must include monorepo root for `rag/` and `research/` (see `backend/render.yaml`); set secrets in dashboard |
| **Database → Render Postgres** | Create a Postgres instance and set `DATABASE_URL` on the API service (blueprint wires `trustmind-db`). Without this, login history cannot persist across redeploys. Startup runs `create_all` — no manual migration step. If the API fails to boot after a DB change, check Render logs for `Database initialisation failed`. **Backups:** see [`docs/ops/BACKUPS.md`](docs/ops/BACKUPS.md). **Launch security (secrets, CORS, spend caps):** see [`docs/ops/SECURITY.md`](docs/ops/SECURITY.md). |

**Logged-in history:** while signed in, Analyse defaults to **Save this check-in to my history**. Dashboard loads `/api/v1/check-ins` with the Bearer token from `localStorage`. Anonymous / private (save off) never writes cross-device history.

Health after deploy: `GET /health` should report a current `version` (e.g. `1.2.1+`).

---

## Known limitations

- Free Render cold starts can delay the first request (UI surfaces a wake-up message).
- Free / starter Postgres may lack automated backups — see [`docs/ops/BACKUPS.md`](docs/ops/BACKUPS.md).
- Evaluation labels are **theme proxies** on a synthetic corpus, not clinical diagnoses.
- Domain shift: synthetic informal posts vs NHS-style KB.
- Source-agreement and evidence “why retrieved” text use **heuristics/templates**, not clinician review.
- Consistency runs increase latency/cost.
- Antivirus on uploads is not included in MVP.

---

## Citation / academic context

- **Product & experiments:** TrustMind AI — UWE MSc AI group dissertation project.  
- **Evaluation dataset:** TrustMind Synthetic Wellbeing v2 (SWMH-compatible schema) — `datasets/synthetic_wellbeing/` (harder template generation; seed 42; N=2500).  
- **Historical motivation (not used as data):** Ji et al. (2021) SWMH paper — [https://doi.org/10.1007/s00521-021-06208-y](https://doi.org/10.1007/s00521-021-06208-y)

---

## License / use

Academic demonstration project. Not a medical device. Do not use for emergency decision-making. If you or someone else is in crisis, contact local emergency services or Samaritans (UK): **116 123**.
