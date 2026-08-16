# TrustMind AI

**Trustworthy, non-diagnostic wellbeing assessment** — MSc Artificial Intelligence (UWE Bristol).  
Compare a **standalone LLM** with **LLM + hybrid RAG** over an allow-listed knowledge base, with calibrated confidence, grounding, abstention, and multimodal input.

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

> **First open note:** the free Render backend may cold-start (up to ~50s on first request). Then try **LLM** and **LLM+RAG** on the analyse page.

---

## What it does

1. User shares how they feel (**typed text**, optional **speech / image / PDF**).
2. They choose **LLM** (model only) or **LLM+RAG** (grounded in approved sources).
3. Backend runs GPT-4.1 (with optional hybrid **BM25 + FAISS + RRF** retrieval).
4. Response includes:
   - non-diagnostic **research category** (e.g. Anxiety-related indicators)
   - **calibrated confidence** + **uncertainty**
   - **grounding status** (standalone / limited / grounded)
   - **trust signals** (model / evidence / retrieval — RAG only)
   - **reasoning** (non-diagnostic language)
   - **retrieved sources + evidence cards** (RAG only)
   - **crisis support links** when safety language or high-risk category appears

Uploaded files are **user context only** — never written into the trusted RAG index.

This is **not** clinical diagnosis or a replacement for UWE Wisdom / Health Assured EAP services.

---

## Research question

> To what extent does Retrieval-Augmented Generation (RAG) improve the **trustworthiness, reliability and explainability** of LLM-generated wellbeing assessments compared with a standalone LLM?

### Controlled evaluation (n=100, seed=42, synthetic wellbeing test sample)

| Metric | LLM-only | LLM+RAG (BM25) | Δ (RAG − LLM) |
|--------|----------|----------------|---------------|
| Accuracy | **0.980** | **0.980** | **0.000** |
| Macro-F1 | **0.981** | **0.981** | **+0.000** |
| Precision (macro) | 0.981 | 0.982 | +0.002 |
| Recall (macro) | 0.982 | 0.980 | −0.002 |

**Corpus:** `datasets/synthetic_wellbeing/` (2,500 fictional posts; no Reddit scrape).  
**Interpretation:** on this synthetic theme-label task, reliability was essentially tied; high absolute scores reflect separable template language — do not over-claim clinical validity. **Trustworthiness and explainability** still improve via allow-listed sources and audit trails.  
Full ethical write-up: [`research/results/rq_answer_summary.md`](research/results/rq_answer_summary.md).

---

## Architecture

```
Browser (Next.js · Vercel)  https://trustmind-ai.vercel.app
    │  optional: speech / image / PDF preprocess → user confirms text
    ▼
POST /api/v1/analyse  →  FastAPI (Render)  https://trustmind-ai.onrender.com
    │
    ├─ pipeline_mode=llm  →  GPT-4.1 only
    └─ pipeline_mode=rag  →  BM25 + FAISS → RRF → top-k passages → GPT-4.1
    │
    ▼
Calibrated confidence → abstention (optional) → grounding / trust signals
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
python -m unittest tests.test_multimodal_input tests.test_trust_explainability -v
```

---

## Key environment variables

| Variable | Role |
|----------|------|
| `OPENAI_API_KEY` | Required for LLM / embeddings / multimodal |
| `OPENAI_MODEL` | Default `gpt-4.1` |
| `USE_RAG` | Default for `pipeline_mode=auto` |
| `RAG_TOP_K` | Passages in RAG prompt (default 5) |
| `ENABLE_ABSTENTION` / `CONFIDENCE_THRESHOLD` | Fail-soft labelling |
| `ENABLE_CONFIDENCE_CALIBRATION` / `CONSISTENCY_RUNS` | Multi-run calibration |
| `CORS_ORIGINS` | Include `https://trustmind-ai.vercel.app` in production |
| `NEXT_PUBLIC_API_URL` | Frontend → backend URL |

See `backend/.env.example`, `backend/render.yaml`, `frontend/.env.local.example`.

---

## Deploy

| Target | Notes |
|--------|--------|
| **Frontend → Vercel** | Root `frontend/`; set `NEXT_PUBLIC_API_URL=https://trustmind-ai.onrender.com` |
| **Backend → Render** | `rootDir: backend`; `PYTHONPATH` must include monorepo root for `rag/` and `research/` (see `backend/render.yaml`); set secrets in dashboard |

Health after deploy: `GET /health` should report a current `version` (e.g. `1.2.1+`).

---

## Known limitations

- Free Render cold starts can delay the first request.
- Evaluation labels are **theme proxies** on a synthetic corpus, not clinical diagnoses.
- Domain shift: synthetic informal posts vs NHS-style KB.
- Source-agreement and evidence “why retrieved” text use **heuristics/templates**, not clinician review.
- Consistency runs increase latency/cost.
- Antivirus on uploads is not included in MVP.

---

## Citation / academic context

- **Product & experiments:** TrustMind AI — UWE MSc AI group dissertation project.  
- **Evaluation dataset:** TrustMind Synthetic Wellbeing (SWMH-compatible schema), v1.0 — `datasets/synthetic_wellbeing/` (template-generated; seed 42; N=2500).  
- **Historical motivation (not used as data):** Ji et al. (2021) SWMH paper — [https://doi.org/10.1007/s00521-021-06208-y](https://doi.org/10.1007/s00521-021-06208-y)

---

## License / use

Academic demonstration project. Not a medical device. Do not use for emergency decision-making. If you or someone else is in crisis, contact local emergency services or Samaritans (UK): **116 123**.
