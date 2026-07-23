# TrustMind AI

MSc Artificial Intelligence dissertation (UWE Bristol): trustworthy text-based wellbeing support with optional Retrieval-Augmented Generation (RAG).

## Research question

> To what extent does Retrieval-Augmented Generation (RAG) improve the trustworthiness, reliability and explainability of LLM-generated wellbeing assessments compared with a standalone LLM?

## Experimental arms

| Mode | Path | Description |
|------|------|-------------|
| **LLM-only** | `research/llm_baseline.py` + `02_LLM_Baseline.ipynb` | Standalone GPT-4.1 (unchanged) |
| **LLM+RAG** | `rag/` + `04_RAG_Evaluation.ipynb` | Hybrid BM25+FAISS retrieval → GPT-4.1 |

Both arms use the same model, temperature, seed, sample size, and SWMH test split for a fair comparison.

## RAG pipeline

```
User Input → Embed Query → Hybrid Retrieve (BM25 + FAISS)
         → Top-K passages → Prompt Builder → GPT-4.1
         → prediction / confidence / reasoning / retrieved_sources
```

### Folder tree (RAG-related)

```
trustmind-ai/
├── rag/                          # Core RAG library
│   ├── config.py                 # Models, top-k, chunk size, paths, USE_RAG
│   ├── chunking.py
│   ├── embeddings_store.py
│   ├── faiss_store.py            # load_index(), search_vector()
│   ├── bm25_store.py             # search_keywords()
│   ├── retriever.py              # Hybrid RRF merge → Top-5
│   ├── prompt_builder.py
│   ├── rag_pipeline.py
│   └── logging_utils.py
├── scripts/
│   ├── chunk_documents.py
│   ├── generate_embeddings.py
│   ├── build_faiss.py
│   ├── build_bm25.py
│   └── demo_rag_query.py
├── knowledge_base/
│   ├── cleaned/                  # Collected Markdown (pending review)
│   ├── review/approved/          # Preferred RAG corpus
│   ├── chunks/                   # chunks.jsonl (+ per-source JSONL)
│   ├── embeddings/               # embeddings.npy + metadata
│   └── indexes/{faiss,bm25}/
├── research/
│   ├── 02_LLM_Baseline.ipynb     # Arm A (do not change for parity)
│   ├── 04_RAG_Evaluation.ipynb   # Arm B evaluation
│   ├── 05_RAG_Comparison.ipynb   # Side-by-side metrics
│   ├── llm_baseline.py
│   └── compare_rag.py
└── requirements-rag.txt
```

## Installation

```bash
cd trustmind-ai
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-rag.txt
```

Set `OPENAI_API_KEY` in `research/.env` (and optionally `backend/.env`).

## Build indexes

```bash
# 1) Chunk documents (500 words, 100 overlap)
python scripts/chunk_documents.py --force

# 2) Embeddings (skipped automatically if already present)
python scripts/generate_embeddings.py

# 3) FAISS + BM25
python scripts/build_faiss.py
python scripts/build_bm25.py
```

**Document source:** prefers `knowledge_base/review/approved/`.  
If that folder is empty, set `ALLOW_PENDING_CLEANED=true` (default) to index `cleaned/` excluding rejected files. Promote important docs to `review/approved/` before claiming a production-ready corpus.

## Demo query

```bash
python scripts/demo_rag_query.py --query "I feel anxious before exams and my heart races"
python scripts/demo_rag_query.py --query "I feel anxious before exams" --classify
```

## Evaluation (dissertation)

```bash
# Arm A already completed → research/results/llm_baseline_*.json/csv
# Arm B:
jupyter notebook research/04_RAG_Evaluation.ipynb
# Then compare:
jupyter notebook research/05_RAG_Comparison.ipynb
```

Outputs:
- `research/results/rag_predictions.csv`
- `research/results/rag_metrics.json`
- `research/results/llm_vs_rag_comparison.csv`
- `research/figures/rag_confusion_matrix.png`
- `research/figures/llm_vs_rag_metrics.png`

## Application architecture (demo)

```
Frontend (Next.js)
    ↓  POST /api/v1/analyse
FastAPI backend
    ↓  USE_RAG ?
LLM pipeline  or  RAG pipeline (BM25+FAISS → GPT)
    ↓
Abstention check (CONFIDENCE_THRESHOLD)
    ↓
Support resources (if SuicideWatch / crisis)
    ↓
JSON response (prediction, confidence, reasoning, sources, ethics fields)
```

The frontend **never** calls OpenAI directly.

### Switch LLM vs RAG

In `backend/.env`:

```bash
USE_RAG=false   # Mode A — standalone LLM
USE_RAG=true    # Mode B — hybrid RAG
```

Restart the API after changing this flag.

### Abstention

```bash
ENABLE_ABSTENTION=true
CONFIDENCE_THRESHOLD=0.75
```

If model confidence &lt; threshold → `status: "abstained"`, `prediction: null`, and a support recommendation (no fabricated label).

### Support resources

When prediction is `SuicideWatch` (or crisis sources are retrieved) and `ENABLE_SUPPORT_RESOURCES=true`, the API returns NHS / Samaritans / Student Minds / UWE links as **support services**, not diagnoses.

### Ethics (always returned)

- Disclaimer (not a medical diagnosis)
- Privacy notice (no unnecessary text storage)
- Transparency (`pipeline_used`: `LLM` or `LLM+RAG`)
- Explainability (reasoning + sources + confidence)
- Human oversight notice

### Run the app

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

OpenAPI docs: http://127.0.0.1:8000/docs

Analyse logs: `knowledge_base/logs/analyse/`

---


| Variable | Default | Meaning |
|----------|---------|---------|
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embeddings |
| `OPENAI_MODEL` / `GPT_MODEL` | `gpt-4.1` | Chat model (same as baseline) |
| `CHUNK_SIZE_WORDS` | `500` | Chunk size |
| `CHUNK_OVERLAP_WORDS` | `100` | Overlap |
| `RAG_TOP_K` | `5` | Passages in the prompt |
| `TEMPERATURE` | `0.0` | Research temperature |
| `ALLOW_PENDING_CLEANED` | `true` | Index cleaned/ if approved/ empty |
| `USE_RAG` | `false` | Backend Mode B switch |
| `OPENAI_API_KEY` | — | Required for embed + generate |

## Logging

Each RAG call appends to:
- `knowledge_base/logs/rag/rag_runs.jsonl` (passages, scores, latency, response preview)
- `knowledge_base/logs/rag/rag_pipeline.log`

## How this answers the research question

1. **Reliability** — Identical evaluation protocol (accuracy, macro-P/R/F1, confusion matrix) on the same SWMH sample for LLM-only vs LLM+RAG.
2. **Trustworthiness** — Generations are constrained to cite retrieved NHS / Student Minds / Samaritans / UWE passages rather than unconstrained parametric memory alone.
3. **Explainability** — Outputs include `reasoning` plus `retrieved_sources` / passage scores, enabling audit of *why* a label was suggested.

The comparison notebook quantifies metric deltas and retrieval statistics so the dissertation can report the *extent* of any improvement (or lack thereof).
