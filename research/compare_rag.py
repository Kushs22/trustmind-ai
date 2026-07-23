"""Compare LLM-only vs LLM+RAG evaluation outputs for TrustMind dissertation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def load_metrics(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def comparison_table(
    baseline_metrics: dict[str, Any],
    rag_metrics: dict[str, Any],
) -> pd.DataFrame:
    """Build a side-by-side metrics table with absolute deltas."""
    b = baseline_metrics.get("metrics", baseline_metrics)
    r = rag_metrics.get("metrics", rag_metrics)
    rows = []
    for key, label in [
        ("accuracy", "Accuracy"),
        ("precision_macro", "Precision (macro)"),
        ("recall_macro", "Recall (macro)"),
        ("f1_macro", "Macro F1"),
    ]:
        bv = float(b.get(key, 0.0))
        rv = float(r.get(key, 0.0))
        rows.append(
            {
                "metric": label,
                "llm_only": bv,
                "llm_rag": rv,
                "delta_rag_minus_baseline": rv - bv,
            }
        )
    return pd.DataFrame(rows)


def retrieval_stats(predictions_csv: Path) -> dict[str, Any]:
    """Summarise retrieval usage from rag_predictions.csv if columns exist."""
    df = pd.read_csv(predictions_csv)
    stats: dict[str, Any] = {"n_rows": len(df)}
    if "n_retrieved" in df.columns:
        stats["mean_n_retrieved"] = float(df["n_retrieved"].mean())
        stats["median_n_retrieved"] = float(df["n_retrieved"].median())
    if "confidence" in df.columns:
        stats["mean_confidence"] = float(df["confidence"].mean())
        stats["median_confidence"] = float(df["confidence"].median())
    if "latency_ms" in df.columns:
        stats["mean_latency_ms"] = float(df["latency_ms"].mean())
        stats["median_latency_ms"] = float(df["latency_ms"].median())
    if "retrieved_sources" in df.columns:
        nonempty = df["retrieved_sources"].fillna("").astype(str).str.len() > 2
        stats["pct_with_sources"] = float(nonempty.mean())
    return stats


def write_comparison_artifacts(
    *,
    baseline_metrics_path: Path,
    rag_metrics_path: Path,
    rag_predictions_path: Path,
    out_dir: Path,
) -> dict[str, Any]:
    """Write comparison CSV/JSON under research/results/."""
    out_dir.mkdir(parents=True, exist_ok=True)
    baseline = load_metrics(baseline_metrics_path)
    rag = load_metrics(rag_metrics_path)
    table = comparison_table(baseline, rag)
    table_path = out_dir / "llm_vs_rag_comparison.csv"
    table.to_csv(table_path, index=False)

    summary = {
        "baseline_experiment": baseline.get("experiment", "llm_only_baseline"),
        "rag_experiment": rag.get("experiment", "llm_rag"),
        "comparison_table": table.to_dict(orient="records"),
        "retrieval_stats": retrieval_stats(rag_predictions_path)
        if rag_predictions_path.exists()
        else {},
    }
    summary_path = out_dir / "llm_vs_rag_comparison.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
