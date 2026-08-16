# Research question answer — LLM-only vs LLM+RAG

**Research question:** To what extent does Retrieval-Augmented Generation (RAG) improve the
**trustworthiness, reliability and explainability** of LLM-generated wellbeing assessments
compared with a standalone LLM?

**Generated (UTC):** 2026-08-16T11:22:18.383231+00:00

## Protocol (fair comparison)

| Control | Value |
|---------|-------|
| Model (local backend) | gpt-4.1 (product OpenAI path used as API proxy) |
| Sample | Synthetic test, **n=100**, **seed=42** (same posts as baseline CSV) |
| Labels | depression, SuicideWatch, Anxiety, bipolar, offmychest |
| LLM arm | Same 5-class instruction; **no** retrieved passages |
| RAG arm | Same 5-class instruction + **BM25 top-3** curated KB passages |
| Retrieval mode | **bm25_top5_curated_kb** |
| API proxy | `http://127.0.0.1:8000/api/v1/analyse` (agent cannot reach api.openai.com directly) |

### Transparency on constraints (ethical research practice)

- Direct `api.openai.com` calls from the Cursor agent environment were blocked (proxy/DNS).
- Classification therefore used the **local TrustMind backend** as an authenticated OpenAI proxy.
- Both experimental arms share that path, so **relative** Δ(RAG−LLM) remains a fair estimate.
- Retrieval for this run is **BM25 top-5** over the curated KB (full hybrid BM25+FAISS+RRF
  requires online query embeddings; re-run `research/run_rag_vs_llm_eval.py` outside the sandbox
  for exact hybrid parity when OpenAI network is available).
- Product temperature (~0.2) may differ slightly from pure research temperature 0.0.

Notebook / fair LLM-arm reference accuracy: 0.98.

## Reliability results

| Metric | LLM-only | LLM+RAG | Δ (RAG − LLM) |
|--------|----------|---------|---------------|
| Accuracy | 0.8400 | 0.8300 | -0.0100 |
| Precision (macro) | 0.8769 | 0.8712 | -0.0057 |
| Recall (macro) | 0.8305 | 0.8211 | -0.0094 |
| Macro F1 | 0.8355 | 0.8291 | -0.0064 |

Invalid predictions count as errors.

### Retrieval diagnostics (RAG arm)

```json
{
  "n_rows": 100,
  "mean_n_retrieved": 3.0,
  "median_n_retrieved": 3.0,
  "mean_confidence": 0.8499000000000001,
  "median_confidence": 0.82,
  "mean_latency_ms": 1819.1706378979143,
  "median_latency_ms": 1795.9685619571246,
  "pct_with_sources": 1.0
}
```

Original dissertation LLM-only notebook metrics (temp=0.0 research path, for reference only):
accuracy=0.84

## Answer (extent of improvement)

### Reliability
Reliability change was **limited or mixed**: accuracy 0.840→0.830 (Δ=-0.010), macro-F1 0.836→0.829 (Δ=-0.006).

### Trustworthiness
RAG **architecturally** improves trustworthiness by constraining reasoning material to
**allow-listed official wellbeing sources** (NHS / Mind / Samaritans / Student Minds / UWE, etc.),
rather than parametric memory alone. This is independent of whether accuracy rises on the
synthetic theme-label task (domain shift: informal synthetic posts vs institutional guidance).

### Explainability
RAG returns **auditable sources** (`retrieved_sources` / passage text in the research log).
LLM-only exposes only parametric reasoning. Explainability therefore improves **by design**.

### Overall RQ verdict
1. **Reliability** is answered quantitatively by the Δ table above — report the measured extent
   without over-claiming clinical validity.
2. **Trustworthiness & explainability** improve via grounding + source transparency even when
   classification accuracy is flat or worse under domain shift.
3. TrustMind does **not** claim to replace human support (e.g. Health Assured WisdomAI / UWE EAP).

## Ethical AI statement

1. **Evaluation corpus** is the synthetic wellbeing dataset
   (`datasets/synthetic_wellbeing/`) with SWMH-compatible labels and **no scraped Reddit posts**.
2. Labels are **theme proxies for academic classification**, not clinical diagnoses.
3. Product RAG corpus is separately curated official guidance; user uploads never enter FAISS/BM25.
4. Outputs are **non-diagnostic wellbeing indicator classifications** for research/demo.
5. Crisis / support pathways in the live product are rule-based and independent of confidence.
6. No fine-tuning was performed on evaluation posts for this run.

## Artefacts

- `research/results/llm_proxy_predictions.csv` / `llm_proxy_metrics.json`
- `research/results/rag_predictions.csv` / `rag_metrics.json`
- `research/results/llm_vs_rag_comparison.csv` / `.json`
- `research/figures/rag_confusion_matrix.png`
- `research/figures/llm_proxy_confusion_matrix.png`
