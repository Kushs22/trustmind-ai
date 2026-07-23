"""
LLM-only baseline helpers for TrustMind AI.

No RAG / retrieval. Used by research/02_LLM_Baseline.ipynb.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import pandas as pd

VALID_LABELS = (
    "depression",
    "SuicideWatch",
    "Anxiety",
    "bipolar",
    "offmychest",
)

LABEL_ALIASES = {
    "depression": "depression",
    "self.depression": "depression",
    "suicidewatch": "SuicideWatch",
    "self.suicidewatch": "SuicideWatch",
    "anxiety": "Anxiety",
    "self.anxiety": "Anxiety",
    "bipolar": "bipolar",
    "self.bipolar": "bipolar",
    "offmychest": "offmychest",
    "self.offmychest": "offmychest",
}


def normalize_label(label: Any) -> str:
    """Map SWMH / model labels to the canonical short form."""
    if label is None or (isinstance(label, float) and pd.isna(label)):
        return ""
    key = str(label).strip()
    mapped = LABEL_ALIASES.get(key, LABEL_ALIASES.get(key.lower().replace(" ", ""), ""))
    return mapped


def build_prompt(post_text: str) -> str:
    """Build the classification prompt for one Reddit post."""
    return f"""You are an AI system analysing Reddit posts for mental wellbeing research.

Classify the following Reddit post into EXACTLY ONE of these labels:

- depression
- SuicideWatch
- Anxiety
- bipolar
- offmychest

Return ONLY valid JSON in this format:

{{
  "predicted_label": "",
  "confidence": 0.0,
  "reasoning": ""
}}

Post:

{post_text}
"""


def extract_json_object(text: str) -> dict[str, Any] | None:
    """
    Safely parse a JSON object from a model response.

    Handles markdown fences and leading/trailing prose.
    """
    if not text or not str(text).strip():
        return None

    cleaned = str(text).strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        return None
    return None


def parse_prediction(response_text: str) -> dict[str, Any]:
    """
    Parse model output into predicted_label, confidence, reasoning.

    Returns a structured dict even when parsing fails.
    """
    parsed = extract_json_object(response_text)
    if parsed is None:
        return {
            "predicted_label": "",
            "confidence": 0.0,
            "reasoning": "",
            "parse_ok": False,
            "error": "invalid_json_or_empty_response",
            "raw_response": (response_text or "")[:2000],
        }

    raw_label = parsed.get("predicted_label", "")
    label = normalize_label(raw_label)
    if label not in VALID_LABELS:
        label = ""

    confidence = parsed.get("confidence", 0.0)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    reasoning = parsed.get("reasoning", "")
    if reasoning is None:
        reasoning = ""
    reasoning = str(reasoning).strip()

    return {
        "predicted_label": label,
        "confidence": confidence,
        "reasoning": reasoning,
        "parse_ok": bool(label),
        "error": "" if label else "invalid_or_missing_label",
        "raw_response": (response_text or "")[:2000],
    }


def load_and_sample_test(
    test_csv: Path,
    sample_size: int,
    random_seed: int,
) -> pd.DataFrame:
    """Load test.csv, normalise labels, and sample rows."""
    df = pd.read_csv(test_csv, encoding="utf-8")
    if "text" not in df.columns or "label" not in df.columns:
        raise ValueError(f"Expected columns text,label in {test_csv}")

    out = df[["text", "label"]].copy()
    out["text"] = out["text"].astype(str)
    out["true_label"] = out["label"].map(normalize_label)
    out = out[out["true_label"].isin(VALID_LABELS)].reset_index(drop=True)

    n = min(sample_size, len(out))
    sample = out.sample(n=n, random_state=random_seed).reset_index(drop=True)
    return sample[["text", "true_label"]]


def call_openai_json(
    client: Any,
    *,
    model_name: str,
    prompt: str,
    temperature: float,
    max_retries: int = 5,
    base_sleep: float = 2.0,
) -> tuple[str, str]:
    """
    Call OpenAI chat completions and return (response_text, error_message).

    Retries on rate limits / transient failures. Never raises for API errors.
    """
    last_error = ""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a careful research assistant. "
                            "Respond with valid JSON only."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            if content is None or not str(content).strip():
                last_error = "empty_response"
                time.sleep(base_sleep * (attempt + 1))
                continue
            return str(content), ""
        except Exception as exc:  # noqa: BLE001 — continue pipeline on any API failure
            last_error = f"{type(exc).__name__}: {exc}"
            message = str(exc).lower()
            # Rate-limit / transient backoff
            if any(tok in message for tok in ("rate", "429", "timeout", "temporar")):
                time.sleep(base_sleep * (2**attempt))
            else:
                time.sleep(base_sleep * (attempt + 1))
    return "", last_error or "api_failure"


def run_baseline_inference(
    sample_df: pd.DataFrame,
    client: Any,
    *,
    model_name: str,
    temperature: float,
    sleep_between_calls: float = 0.5,
    progress_every: int = 10,
    max_retries: int = 5,
) -> pd.DataFrame:
    """
    Classify each post with the LLM (no RAG).

    Continues on per-row failures and records error metadata.
    """
    rows: list[dict[str, Any]] = []
    total = len(sample_df)

    for i, row in sample_df.iterrows():
        idx = int(i) + 1
        text = str(row["text"])
        true_label = str(row["true_label"])
        prompt = build_prompt(text)

        response_text, api_error = call_openai_json(
            client,
            model_name=model_name,
            prompt=prompt,
            temperature=temperature,
            max_retries=max_retries,
        )

        if api_error and not response_text:
            pred = {
                "predicted_label": "",
                "confidence": 0.0,
                "reasoning": "",
                "parse_ok": False,
                "error": api_error,
                "raw_response": "",
            }
        else:
            pred = parse_prediction(response_text)
            if api_error and not pred["error"]:
                pred["error"] = api_error

        rows.append(
            {
                "text": text,
                "true_label": true_label,
                "predicted_label": pred["predicted_label"],
                "confidence": pred["confidence"],
                "reasoning": pred["reasoning"],
                "parse_ok": pred["parse_ok"],
                "error": pred["error"],
            }
        )

        if progress_every and idx % progress_every == 0:
            print(f"Processed {idx}/{total} posts...")

        if sleep_between_calls > 0:
            time.sleep(sleep_between_calls)

    return pd.DataFrame(rows)


def compute_metrics(y_true: list[str], y_pred: list[str]) -> dict[str, Any]:
    """Compute dissertation evaluation metrics with sklearn."""
    from sklearn.metrics import (
        classification_report,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
    )

    labels = list(VALID_LABELS)
    n = len(y_true)
    n_valid = sum(1 for p in y_pred if p in VALID_LABELS)
    n_invalid = n - n_valid

    # Empty / invalid predictions never match a true label → count as errors.
    accuracy = float(sum(t == p for t, p in zip(y_true, y_pred)) / n) if n else 0.0

    # sklearn metrics over the five SWMH classes only.
    metrics = {
        "n_samples": n,
        "n_valid_predictions": n_valid,
        "n_invalid_predictions": n_invalid,
        "accuracy": accuracy,
        "precision_macro": float(
            precision_score(
                y_true, y_pred, labels=labels, average="macro", zero_division=0
            )
        ),
        "recall_macro": float(
            recall_score(
                y_true, y_pred, labels=labels, average="macro", zero_division=0
            )
        ),
        "f1_macro": float(
            f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)
        ),
        "labels": labels,
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "classification_report": classification_report(
            y_true, y_pred, labels=labels, zero_division=0, output_dict=True
        ),
        "classification_report_text": classification_report(
            y_true, y_pred, labels=labels, zero_division=0
        ),
    }
    return metrics
