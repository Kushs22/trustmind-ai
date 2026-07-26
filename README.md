# TrustMind AI

MSc Artificial Intelligence dissertation (UWE Bristol): trustworthy wellbeing support with optional Retrieval-Augmented Generation (RAG), calibrated confidence, and multimodal user input.

## Live demo

| Surface | URL |
|---------|-----|
| **Frontend** | [https://trustmind-ai.vercel.app](https://trustmind-ai.vercel.app) |
| **Analyse page** | [https://trustmind-ai.vercel.app/analyse](https://trustmind-ai.vercel.app/analyse) |
| **Backend API** | [https://trustmind-ai.onrender.com](https://trustmind-ai.onrender.com) |
| **API docs** | [https://trustmind-ai.onrender.com/docs](https://trustmind-ai.onrender.com/docs) |

Repository: [https://github.com/Kushs22/trustmind-ai](https://github.com/Kushs22/trustmind-ai)

### What the live product includes

- **LLM** and **LLM+RAG** assessment modes (user-selectable on the analyse page)
- Optional **typed text**, **microphone / speech**, **image**, and **PDF** input with a confirmation step
- Hybrid **BM25 + FAISS** retrieval over approved wellbeing sources
- **Calibrated confidence**, uncertainty bands, abstention, and grounding status
- **Trust signals** (model confidence / evidence strength / retrieval quality)
- Safety-first **support resources** (independent of confidence and retrieval)
- Privacy mode (default): no unnecessary retention of text, audio, images, or PDFs

Uploaded files are **user context only** — they are never added to the trusted RAG knowledge base and do not count as grounding evidence.

## Research question

> To what extent does Retrieval-Augmented Generation (RAG) improve the trustworthiness, reliability and explainability of LLM-generated wellbeing assessments compared with a standalone LLM?

## Experimental arms

| Mode | Path | Description |
|------|------|-------------|
| **LLM-only** | `research/llm_baseline.py` + `02_LLM_Baseline.ipynb` | Standalone GPT-4.1 (unchanged for eval parity) |
| **LLM+RAG** | `rag/` + `04_RAG_Evaluation.ipynb` | Hybrid BM25+FAISS retrieval → GPT-4.1 |

Both arms use the same model, temperature, seed, sample size, and SWMH test split for a fair comparison.

## Application architecture (product)

```
Frontend (Next.js / Vercel)
    ↓  optional: /api/v1/transcribe | /process-image | /process-pdf
    ↓  user confirms inputs
    ↓  POST /api/v1/analyse  (typed + speech + extracted file text)
FastAPI backend (Render)
    ↓  pipeline_mode: llm | rag | auto
LLM pipeline  or  RAG pipeline (BM25+FAISS → GPT)
    ↓
Calibrated confidence → abstention → grounding / trust signals
    ↓
Support resources if crisis language or high-risk label
    ↓
JSON response (never exposes API keys; uploads not in retrieved_evidence)
```

The frontend **never** calls OpenAI directly.

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

## Application architecture (demo / local)

```
Frontend (Next.js)
    ↓  POST /api/v1/analyse
FastAPI backend
    ↓  USE_RAG / pipeline_mode ?
LLM pipeline  or  RAG pipeline (BM25+FAISS → GPT)
    ↓
Abstention check (CONFIDENCE_THRESHOLD)
    ↓
Support resources (if SuicideWatch / crisis)
    ↓
JSON response (prediction, confidence, reasoning, sources, ethics fields)
```

### Switch LLM vs RAG

Per request on the analyse page (`pipeline_mode`: `llm` | `rag` | `auto`), or in `backend/.env`:

```bash
USE_RAG=false   # Mode A — standalone LLM (when pipeline_mode is auto)
USE_RAG=true    # Mode B — hybrid RAG (when pipeline_mode is auto)
```

Restart the API after changing the server flag.

### Abstention

```bash
ENABLE_ABSTENTION=true
CONFIDENCE_THRESHOLD=0.75
```

If calibrated confidence &lt; threshold → `status: "abstained"`, `prediction: null`, and a support recommendation (no fabricated label).

### Support resources

When prediction is `SuicideWatch` (or crisis language / crisis sources are detected) and `ENABLE_SUPPORT_RESOURCES=true`, the API returns NHS / Samaritans / Student Minds / UWE links as **support services**, not diagnoses.

### Ethics (always returned)

- Disclaimer (not a medical diagnosis)
- Privacy notice (no unnecessary storage of text / media)
- Transparency (`pipeline_used`: `LLM` or `LLM+RAG`)
- Explainability (reasoning + sources + confidence details)
- Human oversight notice

### Run the app locally

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

Open http://localhost:3000/analyse and http://127.0.0.1:8000/docs

Analyse logs: `knowledge_base/logs/analyse/`

---

## Key configuration variables

| Variable | Default | Meaning |
|----------|---------|---------|
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embeddings |
| `OPENAI_MODEL` / `GPT_MODEL` | `gpt-4.1` | Chat model (same as baseline) |
| `CHUNK_SIZE_WORDS` | `500` | Chunk size |
| `CHUNK_OVERLAP_WORDS` | `100` | Overlap |
| `RAG_TOP_K` | `5` | Passages in the prompt |
| `TEMPERATURE` | `0.0` | Research temperature |
| `ALLOW_PENDING_CLEANED` | `true` | Index cleaned/ if approved/ empty |
| `USE_RAG` | `false` | Backend Mode B switch (auto mode) |
| `OPENAI_API_KEY` | — | Required for embed + generate + multimodal |
| `TRANSCRIPTION_MODEL` | `whisper-1` | Speech-to-text model |
| `IMAGE_PROCESSING_MODEL` | `gpt-4.1` | Vision extract model |

## Logging

Each RAG call appends to:
- `knowledge_base/logs/rag/rag_runs.jsonl` (passages, scores, latency, response preview)
- `knowledge_base/logs/rag/rag_pipeline.log`

## Trust and explainability design

TrustMind separates **research classification** from **clinical diagnosis**. Stored labels remain SWMH classes (`depression`, `Anxiety`, `SuicideWatch`, `bipolar`, `offmychest`). The UI shows display names such as “Depression-related indicators”.

### Three trust signals

| Signal | Meaning | Formula (0–100) |
|--------|---------|-----------------|
| **Model confidence** | Final calibrated classification confidence | Calibrated overall score |
| **Evidence strength** | How strongly retrieved evidence supports the prediction | `0.6 × source_agreement + 0.4 × classification_consistency` |
| **Retrieval quality** | Relevance / adequacy of retrieved passages | `0.6 × retrieval_similarity + 0.4 × retrieval_coverage` |

Standalone **LLM** mode marks Evidence strength and Retrieval quality as **Not applicable** (null in the API)—never misleading zeros.

### Confidence calibration

**LLM+RAG** overall confidence combines:

- 30% retrieval similarity (mean FAISS cosine)
- 20% source agreement
- 20% LLM self-reported confidence
- 20% classification consistency (default 3 runs)
- 10% retrieval coverage

**Standalone LLM** uses a separate formula (retrieval weights are never applied):

- 40% LLM self-reported confidence
- 40% classification consistency across repeated runs
- 20% input clarity (`1 − ambiguity`)

Ambiguity considers short/underspecified text, contradictions, overlapping class cues, missing duration/context, and ordinary non-clinical experiences. Caps: **90%** normal; **75%** substantial ambiguity; **60%** when repeated-run predictions differ.

Component scores are logged under `knowledge_base/logs/analyse/` for dissertation analysis. The UI shows the final percentage plus a **Show confidence details** accordion. Standalone mode does not show retrieved sources, evidence-used cards, or retrieval scores.


### Grounding status

Thresholds (env): `GROUNDING_RETRIEVAL_QUALITY_MIN` (default 55), `GROUNDING_EVIDENCE_STRENGTH_MIN` (default 50).

| Status | When | User label |
|--------|------|------------|
| `grounded` | RAG + scores ≥ thresholds | Grounded with retrieved evidence |
| `limited` | RAG with weak scores | Limited supporting evidence |
| `ungrounded` | RAG with no useful passages | Limited supporting evidence |
| `not_applicable` | LLM-only | Standalone model response |

### Source presentation

Internal IDs (e.g. `NHS_DEP_001`) stay in the API for evaluation and **developer mode** (`?dev=1` or `localStorage.trustmind_dev=1`). Normal users see **Organisation — Title** with optional **View source** links from passage/manifest metadata. Titles and URLs are never invented.

### Evidence used

“Why it was relevant” text is generated with a **deterministic template** from user text ∩ passage tokens (no extra LLM call), using cautious phrasing (“overlap with”, “associated with”) and an explicit non-diagnosis caveat.

### Abstention and safety

- Abstention uses **calibrated** confidence vs `CONFIDENCE_THRESHOLD` and withholds the prediction.
- Crisis support resources are triggered by a **rule-based user-text detector** (and high-risk labels), independent of confidence, retrieval success, or abstention.

### Known limitations

- Consistency runs increase latency/cost (~3× LLM calls when enabled).
- Source-agreement uses topic/keyword heuristics, not clinician review.
- Evidence reasons are template-based and may miss subtle relevance.
- Display labels do not change evaluation metrics on SWMH.

## Multimodal input and safety boundaries

TrustMind accepts optional **typed text**, **speech**, **images**, and **PDFs**. All modalities are normalised into labelled combined text before the existing LLM / LLM+RAG pipeline. The text-analysis pipeline itself is unchanged.

### Architecture

1. **Browser speech recognition** when available (Web Speech API). Mic permission is requested only after the user clicks **Speak**.
2. **Fallback:** MediaRecorder captures audio → `POST /api/v1/transcribe` (configurable provider, default OpenAI Whisper via `TRANSCRIPTION_PROVIDER` / `TRANSCRIPTION_MODEL`).
3. **Images:** `POST /api/v1/process-image` — signature validation, EXIF strip (Pillow), vision extract with a non-diagnostic prompt (`IMAGE_PROCESSING_MODEL`).
4. **PDFs:** `POST /api/v1/process-pdf` — genuine PDF check, reject encrypted files, page/size limits, selectable-text extraction (`pypdf`). Scanned-PDF OCR is off by default (`ENABLE_SCANNED_PDF_OCR`).
5. User **reviews and edits** extracted text, then **Confirm and analyse** → `POST /api/v1/analyse` with JSON multimodal fields (no files on the analyse call).

### User context vs trusted RAG evidence

| User uploads (images / PDFs / audio) | Trusted RAG sources |
|--------------------------------------|---------------------|
| Contextual input only | NHS, Mind, Student Minds, Samaritans, PAPYRUS, UWE, other approved orgs |
| Never added to FAISS / BM25 | Indexed knowledge base only |
| Never labelled as grounding sources | Drive grounding status |
| Deleted after processing in privacy mode | Not user uploads |

Images are **not** used to diagnose medical or psychiatric conditions. Facial expression alone is not used to infer mental state. Crisis language in any modality still triggers support resources independently of confidence and retrieval.

### Supported formats and limits (defaults)

| Modality | Types | Limits |
|----------|-------|--------|
| Audio | webm, mp4, mpeg, wav | 180s, 15 MB |
| Image | JPEG, PNG, WEBP | 5 files, 8 MB, pixel/dimension caps |
| PDF | application/pdf | 3 files, 15 MB, 50 pages |

### Privacy and temporary files

With **Analyse privately** (default): raw audio, images, PDFs, transcripts, and extracted text are not retained after the request; uploads are never written to history or the knowledge base. History (opt-in) stores only an approved summary, never original files. Temporary files use an isolated directory with try/finally cleanup.

### Security controls

- File-size, MIME, and magic-byte signature checks
- Filename sanitisation; no user path handling; no public static upload URLs
- In-memory rate limiting on upload/transcribe routes
- API keys stay on the backend
- Antivirus scanning is **not** included in MVP (documented limitation; `antivirus_scan_hook` is reserved for later)

### Configuration (environment)

```
TRANSCRIPTION_PROVIDER=openai
TRANSCRIPTION_MODEL=whisper-1
IMAGE_PROCESSING_MODEL=gpt-4.1
ENABLE_SCANNED_PDF_OCR=false
MAX_AUDIO_DURATION_SECONDS=180
MAX_AUDIO_SIZE_MB=15
MAX_IMAGE_COUNT=5
MAX_IMAGE_SIZE_MB=8
MAX_PDF_COUNT=3
MAX_PDF_SIZE_MB=15
MAX_PDF_PAGES=50
```

### Tests

```bash
cd backend
python -m unittest tests.test_multimodal_input tests.test_trust_explainability -v
```

### Known multimodal limitations

- Browser speech quality varies by device/browser.
- Vision extraction requires an API key; without it, images return a warning and no text.
- Scanned PDFs need selectable text unless OCR is enabled and extended.
- No antivirus scanning yet.
- Frontend unit tests for mic/upload UI are manual (scenarios A–H in the dissertation notes); no Jest/Vitest runner in this repo yet.

## How this answers the research question

1. **Reliability** — Identical evaluation protocol (accuracy, macro-P/R/F1, confusion matrix) on the same SWMH sample for LLM-only vs LLM+RAG.
2. **Trustworthiness** — Generations are constrained to cite retrieved NHS / Student Minds / Samaritans / UWE passages rather than unconstrained parametric memory alone.
3. **Explainability** — Outputs include `reasoning` plus `retrieved_sources` / passage scores, enabling audit of *why* a label was suggested.

The comparison notebook quantifies metric deltas and retrieval statistics so the dissertation can report the *extent* of any improvement (or lack thereof).
