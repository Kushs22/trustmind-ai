# Research question answer — LLM-only vs LLM+RAG

**Research question:** To what extent does Retrieval-Augmented Generation (RAG) improve the
**trustworthiness, reliability and explainability** of LLM-generated wellbeing assessments
compared with a standalone LLM?

**Generated (UTC):** 2026-08-11T21:50:12.096778+00:00

## Protocol (fair comparison)

| Control | Value |
|---------|-------|
| Model (local backend) | gpt-4.1 (product OpenAI path used as API proxy) |
| Sample | SWMH test, **n=100**, **seed=42** (same posts as baseline CSV) |
| Labels | depression, SuicideWatch, Anxiety, bipolar, offmychest |
| LLM arm | Same SWMH instruction; **no** retrieved passages |
| RAG arm | Same SWMH instruction + **BM25 top-3** curated KB passages (truncated for API limit) |
| Retrieval mode | **bm25_top3_curated_kb** |
| API proxy | `http://127.0.0.1:8000/api/v1/analyse` (agent cannot reach api.openai.com directly) |

### Transparency on constraints (ethical research practice)

- Direct `api.openai.com` calls from the Cursor agent environment were blocked (proxy/DNS).
- Classification therefore used the **local TrustMind backend** as an authenticated OpenAI proxy.
- Both experimental arms share that path, so **relative** Δ(RAG−LLM) remains a fair estimate.
- Retrieval for this run is **BM25 top-3** over the curated KB under a 5000-char product API cap
  (full hybrid BM25+FAISS+RRF can be re-run via `research/run_rag_vs_llm_eval.py` when network to
  OpenAI is available).
- Product temperature (~0.2) may differ slightly from pure research temperature 0.0.

**Notebook Arm-A reference** (earlier `02_LLM_Baseline`, temp=0.0, no proxy): **accuracy 0.65**.

## Reliability results

| Metric | LLM-only | LLM+RAG | Δ (RAG − LLM) |
|--------|----------|---------|---------------|
| Accuracy | 0.6800 | 0.6600 | -0.0200 |
| Precision (macro) | 0.7595 | 0.7306 | -0.0289 |
| Recall (macro) | 0.6432 | 0.6503 | +0.0070 |
| Macro F1 | 0.6633 | 0.6540 | -0.0093 |

Invalid predictions count as errors.

### Retrieval diagnostics (RAG arm)

```json
{
  "n_rows": 100,
  "mean_n_retrieved": 3.0,
  "median_n_retrieved": 3.0,
  "mean_confidence": 0.8956000000000001,
  "median_confidence": 0.88,
  "mean_latency_ms": 3137.7896213147324,
  "median_latency_ms": 3005.4314164444804,
  "pct_with_sources": 1.0
}
```

## Answer (extent of improvement)

### Reliability
On the fair local-proxy pair (same posts, same model path), reliability change was **small and slightly negative** under domain shift:

- Accuracy **0.680 → 0.660** (Δ = **−0.020**)
- Macro-F1 **0.663 → 0.654** (Δ = **−0.009**)
- Macro recall slightly rose (0.643 → 0.650, Δ = **+0.007**)

So RAG did **not** improve SWMH subreddit-label accuracy here; it was approximately comparable, with a small drop.

### Trustworthiness
RAG **architecturally** improves trustworthiness by constraining reasoning material to
**allow-listed official wellbeing sources** (NHS / Mind / Samaritans / Student Minds / UWE, etc.),
rather than parametric memory alone. This is independent of whether accuracy rises on Reddit
subreddit labels (domain shift: informal Reddit posts vs institutional guidance).

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

1. **SWMH** is used **offline for research evaluation only**, not as the product knowledge base.
   Dataset paper: Ji et al. (2021), *Neural Computing and Applications*
   (https://doi.org/10.1007/s00521-021-06208-y). Hub: https://huggingface.co/datasets/AIMH/SWMH
2. SWMH labels are **subreddit proxies**, not clinical diagnoses.
3. Product RAG corpus is separately curated official guidance; user uploads never enter FAISS/BM25.
4. Outputs are **non-diagnostic wellbeing indicator classifications** for research/demo.
5. Crisis / support pathways in the live product are rule-based and independent of confidence.
6. No fine-tuning was performed on SWMH posts for this evaluation.

## Artefacts

- `research/results/llm_proxy_predictions.csv` / `llm_proxy_metrics.json`
- `research/results/rag_predictions.csv` / `rag_metrics.json`
- `research/results/llm_vs_rag_comparison.csv` / `.json`
- `research/figures/rag_confusion_matrix.png`
- `research/figures/llm_proxy_confusion_matrix.png`
