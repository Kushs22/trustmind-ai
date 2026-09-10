# TrustMind AI

A **non-diagnostic wellbeing check-in** that compares a standalone LLM with the **same** LLM plus retrieval (RAG). Built for an MSc Artificial Intelligence dissertation at UWE Bristol.

**Authors:** Kush Sharma (25006692) · Aniket Jakhar (24061300)  
**Supervisor:** S. Missaoui · **Module:** UFCEM1-60-M

> This is not a diagnosis, not therapy, and not a crisis-routing service. Support copy can point toward NHS / Samaritans. It does not decide who someone should see.

---

## Live system

| Surface | URL |
|---------|-----|
| Check-in | [https://trustmind-ai.vercel.app/analyse](https://trustmind-ai.vercel.app/analyse) |
| Site | [https://trustmind-ai.vercel.app](https://trustmind-ai.vercel.app) |
| API | [https://trustmind-ai.onrender.com](https://trustmind-ai.onrender.com) |
| OpenAPI | [https://trustmind-ai.onrender.com/docs](https://trustmind-ai.onrender.com/docs) |
| Repository | [https://github.com/Kushs22/trustmind-ai](https://github.com/Kushs22/trustmind-ai) |

The Render API may cold-start (~50s) on the first request. Then use **LLM** and **LLM+RAG** on the same text.

The browser never calls OpenAI. The check-in UI (TypeScript / Next.js on Vercel) `POST`s to our FastAPI `/api/v1/analyse`. The Python API is what talks to gpt-4.1.

---

## Research question

> To what extent does RAG improve **trustworthiness, reliability, and explainability** compared with the **same** standalone LLM?

Public-guidance RAG was never designed to jump theme accuracy. The result we report is **inspectability on the same model**.

### Reported comparison (Table 3)

| Control | Value |
|---------|--------|
| Corpus | Synthetic Wellbeing **v3.1** (`datasets/synthetic_wellbeing/`) |
| Test set | **n = 500**, seed **42**, **125 / class**, 4 themes |
| Generator | **gpt-4.1**, temperature **0.2**, same theme prompt |
| Arm A | LLM-only — no passages |
| Arm B | LLM+RAG — **BM25 top-3** over the allow-listed knowledge base |
| Labels | `depression`, `Anxiety`, `SuicideWatch`, `offmychest` |

| Metric | LLM-only | LLM+RAG (BM25) | Δ |
|--------|----------|----------------|---|
| Accuracy | **0.818** | **0.828** | **+0.010** |
| Macro-F1 | **0.811** | **0.823** | **+0.012** |
| Precision (macro) | 0.845 | 0.860 | +0.016 |
| Recall (macro) | 0.818 | 0.828 | +0.010 |

| Trustworthiness (τ = 0.75) | LLM-only | LLM+RAG |
|----------------------------|----------|---------|
| Mean confidence | 0.856 | 0.862 |
| Gap (confidence − Acc) | +0.038 | +0.034 |
| Coverage | 0.920 | 0.912 |
| Accuracy when answered | 0.863 | 0.868 |

**How to read this.** Five extra correct labels on 500 posts. Anxiety → offmychest is **51 / 125 on both arms** — retrieval did not move that boundary. RAG narrows the Gap slightly and, unlike Arm A, returns **source cards** the user can open.

Artefacts: [`research/results/llm_vs_rag_comparison.csv`](research/results/llm_vs_rag_comparison.csv) · [`research/results/rq_answer_summary.md`](research/results/rq_answer_summary.md) · matrices in [`research/figures/`](research/figures/).

Older **5-class v3.0** numbers (Acc 0.860 vs 0.832) are **not** this experiment. They are archived at [`research/results/archive_n500_5class_v3.0/`](research/results/archive_n500_5class_v3.0/).

---

## What the product does

1. The user types how they feel (optional speech / image / PDF is confirmed as text first).
2. They choose **LLM** or **LLM+RAG** (`pipeline_mode`).
3. FastAPI returns a **theme**, **confidence**, and (on RAG) **allow-listed passages** as source cards.
4. A stop-rule can hold a thin call. Crisis language can **signpost** NHS / Samaritans. It does not route care.

Uploads are user context only. They are never written into the RAG index.

### Product vs dissertation numbers

The live app **can** run hybrid **BM25 + FAISS + RRF**. **Table 3 does not.** The reported dual-arm uses BM25 top-3 only, so the Δ isolates retrieval of public guidance, not a denser index.

---

## Stack

| Layer | Language | Tools | Role |
|-------|----------|--------|------|
| Website | TypeScript | Next.js, React, Tailwind, Vercel | Check-in UI, Compare LLM ↔ RAG |
| API + LLM | Python | FastAPI, OpenAI SDK, **gpt-4.1** | `POST /api/v1/analyse`, JSON theme + confidence, temp 0.2 |
| RAG | Python | `rank-bm25`, `prompt_builder` | 836 chunks; top-3 passages into the **same** prompt |
| Dataset | Python | `research/generate_synthetic_wellbeing.py` | v3.1, seed 42, 2,500 **fictional** posts |

```
Browser (Next.js · Vercel)
    │  POST JSON  (pipeline_mode = llm | rag)
    ▼
FastAPI  /api/v1/analyse  (Render)
    ├─ llm  →  gpt-4.1  (no passages)
    └─ rag  →  BM25 top-3  →  same gpt-4.1 call
    ▼
Theme + confidence  ·  source cards only if retrieval ran
```

---

## Dataset (ethics-led)

**Synthetic Wellbeing v3.1** — template-generated first-person posts. Not scraped Reddit. Not LLM-written posts. Not live user messages.

| Split | Rows | Per class |
|-------|------|-----------|
| Train | 1,600 | 400 |
| Val | 400 | 100 |
| Test | 500 | 125 (held-out comparison) |
| **Total** | **2,500** | balanced |

Card and generator: [`datasets/synthetic_wellbeing/DATASET_CARD.md`](datasets/synthetic_wellbeing/DATASET_CARD.md) · [`research/generate_synthetic_wellbeing.py`](research/generate_synthetic_wellbeing.py).

Ji et al. (2021) SWMH is **historical motivation only**. It is not the evaluation corpus.

---

## Dissertation files in this repo

| Path | What it is |
|------|------------|
| [`datasets/synthetic_wellbeing/`](datasets/synthetic_wellbeing/) | v3.1 CSVs, splits, dataset card |
| [`research/results/llm_vs_rag_comparison.csv`](research/results/llm_vs_rag_comparison.csv) | Table 3 metrics |
| [`research/results/rq_answer_summary.md`](research/results/rq_answer_summary.md) | RQ write-up for the n=500 run |
| [`research/figures/llm_proxy_confusion_matrix_n500.png`](research/figures/llm_proxy_confusion_matrix_n500.png) | LLM-only matrix |
| [`research/figures/rag_confusion_matrix_n500.png`](research/figures/rag_confusion_matrix_n500.png) | LLM+RAG matrix |
| [`knowledge_base/`](knowledge_base/) | Allow-listed guidance, chunks, BM25/FAISS indexes |
| [`rag/`](rag/) | Retriever + prompt builder |
| [`frontend/`](frontend/) | Next.js check-in |
| [`backend/`](backend/) | FastAPI `/api/v1/analyse` |
| [`research/run_rag_vs_llm_via_local_api.py`](research/run_rag_vs_llm_via_local_api.py) | Fair dual-arm eval runner |

Row-level `*_predictions.csv` files are gitignored (they repeat check-in text). Metrics and the public CSVs are enough to reproduce the table.

---

## Quick start (local)

**API**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # OPENAI_API_KEY, CORS_ORIGINS
uvicorn app.main:app --reload --port 8000
```

**Website**

```bash
cd frontend
npm install
# .env.local: NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
npm run dev
```

Open http://localhost:3000/analyse

**Rebuild indexes** (optional — production indexes are already under `knowledge_base/indexes/`)

```bash
pip install -r requirements-rag.txt
python scripts/chunk_documents.py --force
python scripts/generate_embeddings.py
python scripts/build_faiss.py
python scripts/build_bm25.py
```

**Re-run the reported comparison** (needs a local API with `OPENAI_API_KEY`)

```bash
python research/run_rag_vs_llm_via_local_api.py
```

---

## Trust and safety

| Control | Behaviour |
|---------|-----------|
| Scope | Wellbeing check-in only |
| Abstention | Thin calls can be held (τ = 0.75 in the reported table) |
| Grounding | Source cards appear only when retrieval ran |
| Knowledge base | Allow-list only — no live web crawl |
| Uploads | Never enter BM25 / FAISS |
| Crisis | Signpost; independent of RAG success |
| Eval data | Synthetic v3.1 — no scraped user posts |

---

## Deploy

| Target | Notes |
|--------|--------|
| Frontend → Vercel | Root `frontend/`. `NEXT_PUBLIC_API_URL=https://trustmind-ai.onrender.com` |
| Backend → Render | `rootDir: backend`. `PYTHONPATH` must include the repo root so `rag/` imports. Secrets stay on Render. |
| Database | Render Postgres (`DATABASE_URL`) for signed-in history. SQLite is local-dev only. |

API keys stay on the **server**. See [`docs/ops/SECURITY.md`](docs/ops/SECURITY.md) and [`backend/.env.example`](backend/.env.example).

---

## Known limitations

- Theme labels on synthetic posts are **not** clinical diagnoses.
- Informal check-in language vs institutional guidance is a real domain shift (the shared 51 / 125 Anxiety → offmychest cell is the clearest example).
- Table 3 is BM25. Hybrid FAISS + RRF in the product is not in that table.
- Free Render cold starts delay the first request.
- Evidence “why retrieved” text is heuristic, not clinician-reviewed.

---

## Citation

TrustMind AI — UWE MSc Artificial Intelligence group project (Sharma & Jakhar, 2026).  
Evaluation corpus: Synthetic Wellbeing v3.1, seed 42.  
Historical schema motivation (not used as data): Ji et al. (2021), [doi:10.1007/s00521-021-06208-y](https://doi.org/10.1007/s00521-021-06208-y).

---

## License / use

Academic demonstration. Not a medical device. Do not use for emergency decisions.  
If you or someone else is in crisis, contact local emergency services or Samaritans (UK): **116 123**.
