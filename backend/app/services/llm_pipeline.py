"""Standalone LLM classification pipeline (Mode A) for TrustMind analyse API."""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any

from app.config import settings
from app.services.confidence_calibration import (
    calibrate_llm_only_confidence,
    majority_label,
)
from app.services.evidence_presentation import sanitise_reasoning

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_RESEARCH = _REPO_ROOT / "research"


def _ensure_paths() -> None:
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))
    if str(_RESEARCH) not in sys.path:
        sys.path.insert(0, str(_RESEARCH))


def _build_product_llm_prompt(post_text: str) -> str:
    """
    Product-facing prompt for standalone LLM mode.

    Keeps the same SWMH research labels as the dissertation baseline, with
    cautious non-diagnostic wording requirements.
    """
    return f"""You are an AI system analysing free-text wellbeing check-ins for academic research.

Classify the following text into EXACTLY ONE of these research labels:

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

Reasoning rules:
- Describe observable experiences in the submitted text.
- Prefer phrasing such as "may overlap with", "associated with", or "research category".
- Do NOT say "classic symptoms", "you have", "this proves", or "the diagnosis is".
- End with: this is not a clinical diagnosis.
- Keep reasoning to 2–5 short sentences.

Text:

{post_text}
"""


def run_llm_pipeline(text: str) -> dict[str, Any]:
    """
    Run GPT-only wellbeing classification (no retrieval).

    Uses a standalone confidence formula (not the RAG retrieval formula).
    """
    _ensure_paths()
    from llm_baseline import call_openai_json, parse_prediction
    from openai import OpenAI

    started = time.perf_counter()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for the LLM pipeline")

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = _build_product_llm_prompt(text)
    n_runs = max(1, int(settings.consistency_runs)) if settings.enable_confidence_calibration else 1
    consistency_temp = float(settings.consistency_temperature)
    primary_temp = float(settings.openai_temperature)

    runs: list[dict[str, Any]] = []
    last_error = ""
    for i in range(n_runs):
        temp = primary_temp if i == 0 else max(primary_temp, consistency_temp)
        response_text, api_error = call_openai_json(
            client,
            model_name=settings.openai_model,
            prompt=prompt,
            temperature=temp,
        )
        if api_error and not response_text:
            last_error = api_error
            continue
        parsed = parse_prediction(response_text)
        if api_error and not parsed.get("error"):
            parsed["error"] = api_error
        runs.append(parsed)
        logger.info(
            "llm_consistency_run i=%s/%s label=%s llm_conf=%.3f temp=%.2f",
            i + 1,
            n_runs,
            parsed.get("predicted_label"),
            float(parsed.get("confidence") or 0.0),
            temp,
        )

    if not runs:
        raise RuntimeError(last_error or "empty_response")

    labels = [r.get("predicted_label") or None for r in runs]
    prediction = majority_label(labels) or (runs[0].get("predicted_label") or None)
    reasoning = ""
    llm_conf = float(runs[0].get("confidence") or 0.0)
    for r in runs:
        if str(r.get("predicted_label") or "").lower() == str(prediction or "").lower():
            reasoning = str(r.get("reasoning") or "")
            llm_conf = float(r.get("confidence") or 0.0)
            break
    if not reasoning:
        reasoning = str(runs[0].get("reasoning") or "")
    reasoning = sanitise_reasoning(reasoning)

    if settings.enable_confidence_calibration:
        calibrated = calibrate_llm_only_confidence(
            text=text,
            prediction=prediction,
            llm_confidence=llm_conf,
            run_labels=labels,
        )
        confidence = calibrated.confidence
        breakdown = calibrated.breakdown.to_dict()
        uncertainty = calibrated.uncertainty
        calibration_log = calibrated.to_log_dict()
    else:
        confidence = min(llm_conf, 0.90)
        breakdown = {
            "retrieval_similarity": None,
            "source_agreement": None,
            "llm_confidence": int(round(confidence * 100)),
            "classification_consistency": None,
            "retrieval_coverage": None,
            "input_clarity": None,
        }
        uncertainty = ""
        calibration_log = {}

    latency_ms = (time.perf_counter() - started) * 1000.0
    return {
        "prediction": prediction,
        "confidence": confidence,
        "reasoning": reasoning,
        "sources": [],
        "retrieved_passages": [],
        "pipeline_used": "LLM",
        "latency_ms": latency_ms,
        "error": runs[0].get("error") or "",
        "parse_ok": bool(prediction),
        "confidence_breakdown": breakdown,
        "uncertainty": uncertainty,
        "calibration": calibration_log,
        "consistency_labels": labels,
        "llm_confidence_raw": llm_conf,
    }
