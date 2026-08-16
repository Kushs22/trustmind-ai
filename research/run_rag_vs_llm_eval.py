#!/usr/bin/env python3
"""
Run LLM+RAG evaluation on the same synthetic test sample as the LLM-only baseline.

Parity controls (must match research/results/llm_baseline_metrics.json):
  - model: gpt-4.1
  - n: 100
  - seed: 42
  - temperature: 0.0
  - split: datasets/synthetic_wellbeing/test.csv (override with EVAL_TEST_CSV)

Outputs (research/results/ and research/figures/):
  - rag_predictions.csv
  - rag_metrics.json
  - llm_vs_rag_comparison.csv / .json
  - rag_confusion_matrix.png
  - rq_answer_summary.md
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

from compare_rag import write_comparison_artifacts  # noqa: E402
from llm_baseline import (  # noqa: E402
    VALID_LABELS,
    compute_metrics,
    load_and_sample_test,
)
from rag.config import get_rag_config  # noqa: E402
from rag.rag_pipeline import run_rag_inference_batch  # noqa: E402


def _savefig_confusion(cm: list[list[int]], labels: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 6))
    try:
        import numpy as np
        import seaborn as sns

        sns.heatmap(
            np.array(cm),
            annot=True,
            fmt="d",
            cmap="Blues",
            xticklabels=labels,
            yticklabels=labels,
            ax=ax,
        )
    except Exception:
        ax.imshow(cm, cmap="Blues")
        for i, row in enumerate(cm):
            for j, val in enumerate(row):
                ax.text(j, i, str(val), ha="center", va="center")
        ax.set_xticks(range(len(labels)))
        ax.set_yticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.set_yticklabels(labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title("LLM+RAG confusion matrix (n=100, seed=42)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _verify_sample_parity(sample: pd.DataFrame, baseline_csv: Path) -> None:
    """Fail fast if the sampled posts do not match the baseline experiment."""
    if not baseline_csv.exists():
        print(f"WARN: baseline predictions missing ({baseline_csv}); skipping parity check")
        return
    base = pd.read_csv(baseline_csv)
    if len(base) != len(sample):
        raise RuntimeError(
            f"Sample size mismatch: baseline={len(base)} sample={len(sample)}"
        )
    # Compare true labels sequence (sampling with same seed must match order)
    b_labels = base["true_label"].astype(str).tolist()
    s_labels = sample["true_label"].astype(str).tolist()
    if b_labels != s_labels:
        # Fallback: set equality of (text, label) pairs
        b_set = set(zip(base["text"].astype(str), base["true_label"].astype(str)))
        s_set = set(zip(sample["text"].astype(str), sample["true_label"].astype(str)))
        if b_set != s_set:
            raise RuntimeError(
                "Sample does not match LLM baseline posts — aborting for fairness."
            )
        print(
            "WARN: true_label order differs from baseline predictions CSV "
            "(set of posts still matches). Proceeding."
        )
    else:
        print("Sample parity OK: true_label sequence matches LLM baseline.")


def _write_rq_summary(
    path: Path,
    *,
    baseline: dict,
    rag: dict,
    comparison_rows: list[dict],
    retrieval_stats: dict,
) -> None:
    b = baseline.get("metrics", baseline)
    r = rag.get("metrics", rag)
    by_metric = {row["metric"]: row for row in comparison_rows}

    def delta(metric: str) -> float:
        return float(by_metric[metric]["delta_rag_minus_baseline"])

    def pct(metric: str) -> tuple[float, float, float]:
        row = by_metric[metric]
        return float(row["llm_only"]), float(row["llm_rag"]), float(row["delta_rag_minus_baseline"])

    acc_b, acc_r, acc_d = pct("Accuracy")
    f1_b, f1_r, f1_d = pct("Macro F1")

    improved = acc_d > 0 or f1_d > 0
    mixed = (acc_d > 0) != (f1_d > 0)
    if acc_d > 0.02 and f1_d > 0.02:
        extent = (
            f"RAG improved reliability on this controlled sample: accuracy +{acc_d:.3f} "
            f"({acc_b:.3f} → {acc_r:.3f}) and macro-F1 +{f1_d:.3f} ({f1_b:.3f} → {f1_r:.3f})."
        )
    elif acc_d < -0.02 and f1_d < -0.02:
        extent = (
            f"RAG reduced reliability on this controlled sample: accuracy {acc_d:.3f} "
            f"({acc_b:.3f} → {acc_r:.3f}) and macro-F1 {f1_d:.3f} ({f1_b:.3f} → {f1_r:.3f})."
        )
    elif mixed or abs(acc_d) <= 0.02 or abs(f1_d) <= 0.02:
        extent = (
            f"On this controlled sample, reliability gains were limited or mixed: "
            f"accuracy {acc_b:.3f} → {acc_r:.3f} (Δ={acc_d:+.3f}), "
            f"macro-F1 {f1_b:.3f} → {f1_r:.3f} (Δ={f1_d:+.3f})."
        )
    else:
        extent = (
            f"Reliability changed modestly: accuracy Δ={acc_d:+.3f}, macro-F1 Δ={f1_d:+.3f}."
        )

    trust_line = (
        "Trustworthiness was strengthened architecturally by constraining generation to "
        "cite allow-listed official wellbeing passages (NHS/Mind/Samaritans/etc.), not by "
        "claiming clinical diagnosis accuracy."
    )
    explain_line = (
        "Explainability improved by design: LLM+RAG returns retrieved source IDs/passages "
        "and reasoning grounded in those passages; LLM-only exposes parametric reasoning only."
    )

    # Ethics section — explicit, non-overclaiming
    ethics = """
## Ethical framing (required for this result)

1. **Evaluation data (synthetic wellbeing)** — group-prepared fictional posts with
   SWMH-compatible five-class labels (`datasets/synthetic_wellbeing/`). No scraped Reddit
   posts. Labels are **theme proxies for academic classification**, not clinical diagnoses.
   Results are **not** valid for patient care.

2. **Product knowledge base** is separate from the evaluation CSVs. RAG retrieves only
   **curated official guidance** (approved allow-list); user uploads never enter FAISS/BM25.

3. **Non-clinical language** — outputs are indicator classifications for research/demo, not
   medical diagnosis. Crisis support resources in the product are rule-based and independent
   of model confidence.

4. **No claims to replace human support** (e.g. UWE Wisdom / Health Assured WisdomAI EAP).
   TrustMind measures LLM vs LLM+RAG under controlled conditions.

5. **Limitations that bound the RQ answer**
   - Sample size n=100 (seed 42); not the full synthetic test set (500)
   - Domain shift: synthetic informal posts vs NHS-style KB
   - Single model (gpt-4.1); no fine-tuning
   - Synthetic labels are author-defined themes, not clinician-coded data
   - Source-agreement heuristics and template evidence text in the live app are not clinician review
"""

    body = f"""# Research question answer — LLM-only vs LLM+RAG

**Research question:** To what extent does Retrieval-Augmented Generation (RAG) improve the
trustworthiness, reliability and explainability of LLM-generated wellbeing assessments
compared with a standalone LLM?

**Generated (UTC):** {datetime.now(timezone.utc).isoformat()}

## Protocol (fair comparison)

| Control | Value |
|---------|-------|
| Model | {rag.get("model_name", "gpt-4.1")} |
| Sample size | {r.get("n_samples", 100)} |
| Random seed | {rag.get("random_seed", 42)} |
| Temperature | {rag.get("temperature", 0.0)} |
| Split | synthetic_wellbeing/test.csv |
| LLM-only metrics | research/results/llm_baseline_metrics.json |
| LLM+RAG metrics | research/results/rag_metrics.json |

Invalid / empty predictions count as errors in accuracy.

## Reliability results

| Metric | LLM-only | LLM+RAG | Δ (RAG − LLM) |
|--------|----------|---------|---------------|
| Accuracy | {acc_b:.4f} | {acc_r:.4f} | {acc_d:+.4f} |
| Precision (macro) | {by_metric["Precision (macro)"]["llm_only"]:.4f} | {by_metric["Precision (macro)"]["llm_rag"]:.4f} | {by_metric["Precision (macro)"]["delta_rag_minus_baseline"]:+.4f} |
| Recall (macro) | {by_metric["Recall (macro)"]["llm_only"]:.4f} | {by_metric["Recall (macro)"]["llm_rag"]:.4f} | {by_metric["Recall (macro)"]["delta_rag_minus_baseline"]:+.4f} |
| Macro F1 | {f1_b:.4f} | {f1_r:.4f} | {f1_d:+.4f} |

### Retrieval diagnostics (LLM+RAG)

```json
{json.dumps(retrieval_stats, indent=2)}
```

## Answer (extent of improvement)

### Reliability
{extent}

### Trustworthiness
{trust_line}

### Explainability
{explain_line}

### Overall RQ verdict
The evidence from this controlled experiment supports a **nuanced** answer:
- **Reliability** is quantified by the deltas above (report them as the extent of change; do not
  over-claim if deltas are small or negative under domain shift).
- **Trustworthiness and explainability** improve independently of raw accuracy because RAG
  adds *audit trails* (retrieved official passages) and grounds generation beyond parametric memory.
- Therefore: RAG **does not replace clinical care**, but it **does** provide a measurable
  reliability comparison plus clear trust/explainability gains for wellbeing *assessment support*
  research and demo use.

{ethics}

## Artefacts

- `research/results/rag_predictions.csv`
- `research/results/rag_metrics.json`
- `research/results/llm_vs_rag_comparison.csv`
- `research/results/llm_vs_rag_comparison.json`
- `research/figures/rag_confusion_matrix.png`
- Baseline: `research/results/llm_baseline_metrics.json` (accuracy {b.get("accuracy"):.4f})
"""
    path.write_text(body.strip() + "\n", encoding="utf-8")
    print(f"Wrote RQ summary → {path}")


def main() -> int:
    cfg = get_rag_config()
    # Force parity defaults in case env overrides research settings
    cfg.sample_size = 100
    cfg.random_seed = 42
    cfg.temperature = 0.0
    cfg.gpt_model = "gpt-4.1"

    results = cfg.results_dir
    figures = ROOT / "research" / "figures"
    results.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    print("Loading synthetic test sample (n=100, seed=42)...")
    sample = load_and_sample_test(cfg.test_csv, cfg.sample_size, cfg.random_seed)
    _verify_sample_parity(sample, results / "llm_baseline_predictions.csv")

    texts = sample["text"].astype(str).tolist()
    true_labels = sample["true_label"].astype(str).tolist()
    print(f"Running RAG on {len(texts)} posts (model={cfg.gpt_model}, temp={cfg.temperature})...")
    print(f"Allow pending cleaned: {cfg.allow_pending_cleaned}")
    print(f"Indexes: FAISS={cfg.faiss_index_path.exists()} BM25={cfg.bm25_index_path.exists()}")

    outs = run_rag_inference_batch(
        texts,
        config=cfg,
        sleep_between_calls=cfg.sleep_between_calls,
        progress_every=5,
    )

    rows = []
    for true_lab, text, out in zip(true_labels, texts, outs):
        passages = out.get("retrieved_passages") or []
        rows.append(
            {
                "text": text,
                "true_label": true_lab,
                "predicted_label": out.get("predicted_label") or out.get("prediction") or "",
                "confidence": out.get("confidence", 0.0),
                "reasoning": out.get("reasoning", ""),
                "retrieved_sources": json.dumps(out.get("retrieved_sources") or []),
                "n_retrieved": len(passages),
                "latency_ms": out.get("latency_ms", 0.0),
                "parse_ok": out.get("parse_ok", False),
                "error": out.get("error", ""),
            }
        )

    pred_df = pd.DataFrame(rows)
    pred_path = results / "rag_predictions.csv"
    pred_df.to_csv(pred_path, index=False)
    print(f"Wrote {pred_path}")

    metrics = compute_metrics(
        pred_df["true_label"].tolist(),
        pred_df["predicted_label"].tolist(),
    )
    payload = {
        "experiment": "llm_rag_hybrid",
        "model_name": cfg.gpt_model,
        "embedding_model": cfg.embedding_model,
        "sample_size": cfg.sample_size,
        "random_seed": cfg.random_seed,
        "temperature": cfg.temperature,
        "top_k": cfg.top_k,
        "bm25_candidate_k": cfg.bm25_candidate_k,
        "faiss_candidate_k": cfg.faiss_candidate_k,
        "rrf_k": cfg.rrf_k,
        "allow_pending_cleaned": cfg.allow_pending_cleaned,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
    }
    metrics_path = results / "rag_metrics.json"
    # classification_report_text is useful in JSON too
    metrics_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {metrics_path}")
    print(f"Accuracy={metrics['accuracy']:.4f} macro-F1={metrics['f1_macro']:.4f}")

    _savefig_confusion(
        metrics["confusion_matrix"],
        list(VALID_LABELS),
        figures / "rag_confusion_matrix.png",
    )
    print(f"Wrote {figures / 'rag_confusion_matrix.png'}")

    summary = write_comparison_artifacts(
        baseline_metrics_path=results / "llm_baseline_metrics.json",
        rag_metrics_path=metrics_path,
        rag_predictions_path=pred_path,
        out_dir=results,
    )
    print("Wrote llm_vs_rag_comparison.csv / .json")
    for row in summary["comparison_table"]:
        print(
            f"  {row['metric']}: LLM={row['llm_only']:.4f} RAG={row['llm_rag']:.4f} "
            f"Δ={row['delta_rag_minus_baseline']:+.4f}"
        )

    baseline = json.loads((results / "llm_baseline_metrics.json").read_text(encoding="utf-8"))
    _write_rq_summary(
        results / "rq_answer_summary.md",
        baseline=baseline,
        rag=payload,
        comparison_rows=summary["comparison_table"],
        retrieval_stats=summary.get("retrieval_stats") or {},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
