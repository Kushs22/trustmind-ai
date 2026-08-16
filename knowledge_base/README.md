# TrustMind AI — Knowledge Base

Trusted wellbeing and mental-health **source collection** for the MSc dissertation project TrustMind AI.

This stage prepares documents that may later support Retrieval-Augmented Generation (RAG).  
**RAG, embeddings, FAISS, BM25, chunking, and retrieval are not implemented yet.**

## Purpose

| Resource | Role |
|----------|------|
| **Synthetic wellbeing dataset** | Experimental evaluation data (LLM-only vs LLM+RAG classification) |
| **This knowledge base** | Curated external guidance (NHS, Mind, Samaritans, UWE, …) for grounding |

Only URLs you manually add to the approved list are downloaded. There is **no website crawling** and **no automatic link following**.

## Folder structure

```
knowledge_base/
├── sources/
│   └── approved_sources.csv     # Manual allow-list of URLs
├── raw/                         # Original HTML (audit / reproducibility)
├── cleaned/                     # Extracted Markdown + YAML front matter
├── metadata/
│   └── source_manifest.csv      # Collection audit trail
├── review/
│   ├── approved/                # After you manually approve
│   └── rejected/                # After you manually reject
├── logs/                        # collection.log + validation_report.md
└── README.md
```

## How to add a new approved source

1. Edit `sources/approved_sources.csv`.
2. Add a new row with a unique `source_id` (e.g. `MIND_ANX_001`).
3. Fill organisation, topic, title, url, country, source_type.
4. Set `approved_for_collection` to `true` only when you are ready to download it.
5. Re-run the collector (commands below).

Suggested organisations: NHS, Mind, Student Minds, Samaritans, PAPYRUS, Anxiety UK, UWE Bristol.

## Install dependencies

From the repository root:

```bash
pip install -r requirements-knowledge-base.txt
```

## Run the collector

```bash
python scripts/collect_sources.py
```

Re-download even if already collected:

```bash
python scripts/collect_sources.py --force
```

The collector:

- processes only `approved_for_collection=true` rows
- saves raw HTML to `raw/{source_id}.html`
- saves cleaned Markdown to `cleaned/{source_id}.md`
- updates `metadata/source_manifest.csv`
- sets `review_status=pending` for every new document
- skips duplicates by URL / content hash
- logs to `logs/collection.log`

## Inspect cleaned files

Open files in `cleaned/`. Each file starts with YAML front matter (`source_id`, URL, access time, hash, `review_status`) followed by the article text.

## Manual approve / reject

Collected files are **not** RAG-ready until you review them.

**Approve**

1. Read `cleaned/SOURCE_ID.md`.
2. Copy it to `review/approved/SOURCE_ID.md`.
3. Change front matter `review_status` to `approved`.
4. Update the matching row in `metadata/source_manifest.csv` (`review_status=approved`).

**Reject**

1. Copy/move to `review/rejected/SOURCE_ID.md`.
2. Set `review_status` to `rejected` and note why in `approved_sources.csv` notes or the manifest `error_message` field.

The RAG pipeline prefers documents under `review/approved/`.  
If approved is empty, chunking may fall back to `cleaned/` when `ALLOW_PENDING_CLEANED=true` (research convenience only).

## Validation

```bash
python scripts/validate_knowledge_base.py
```

Writes a readable report to `logs/validation_report.md` covering passes, warnings, failures, duplicates, and pending review items.

## Duplicate detection

- Same **URL** already collected successfully → skip (unless `--force`).
- Same **content hash** as another successful document → mark `collection_status=duplicate`.

## Why keep raw and cleaned copies?

| Copy | Why |
|------|-----|
| **Raw HTML** | Reproducibility, audit, re-extraction if the cleaner improves |
| **Cleaned Markdown** | Human review + chunking / embedding input |

## Dissertation notebooks

- `research/03_Knowledge_Base_Collection.ipynb` — collection stage  
- `research/04_RAG_Evaluation.ipynb` — LLM+RAG evaluation  
- `research/05_RAG_Comparison.ipynb` — vs LLM-only baseline  

## RAG stage (implemented)

From the repository root (see also root `README.md`):

```bash
pip install -r requirements-rag.txt
python scripts/chunk_documents.py --force
python scripts/generate_embeddings.py
python scripts/build_faiss.py
python scripts/build_bm25.py
python scripts/demo_rag_query.py --query "I feel overwhelmed and anxious"
```

Pipeline modules live in `rag/` (chunking, embeddings, FAISS, BM25, hybrid retriever, prompt builder, inference, logging).
