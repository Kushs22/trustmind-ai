"""Standalone LLM classification pipeline (Mode A) for TrustMind analyse API."""

from __future__ import annotations

import json
import logging
import re
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


def _find_repo_root() -> Path:
    """Locate monorepo root whether backend is nested or is the serve root."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "research" / "llm_baseline.py").is_file():
            return parent
        if (parent / "rag" / "config.py").is_file() and (parent / "backend").is_dir():
            return parent
    # Fallbacks for local + Render layouts
    for idx in (3, 2, 4):
        if len(here.parents) > idx:
            return here.parents[idx]
    return here.parents[2]


_REPO_ROOT = _find_repo_root()
_RESEARCH = _REPO_ROOT / "research"

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


def _ensure_paths() -> None:
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))
    if str(_RESEARCH) not in sys.path:
        sys.path.insert(0, str(_RESEARCH))


def _normalize_label(label: Any) -> str:
    if label is None:
        return ""
    key = str(label).strip()
    if key.lower() in {"", "nan", "none", "null"}:
        return ""
    return LABEL_ALIASES.get(key, LABEL_ALIASES.get(key.lower().replace(" ", ""), ""))


def _extract_json_object(text: str) -> dict[str, Any] | None:
    if not text or not str(text).strip():
        return None
    cleaned = str(text).strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()
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


def _parse_prediction_local(response_text: str) -> dict[str, Any]:
    parsed = _extract_json_object(response_text)
    if parsed is None:
        return {
            "predicted_label": "",
            "confidence": 0.0,
            "reasoning": "",
            "parse_ok": False,
            "error": "invalid_json_or_empty_response",
        }
    raw_label = parsed.get("predicted_label", parsed.get("prediction", ""))
    label = _normalize_label(raw_label)
    confidence = parsed.get("confidence", 0.0)
    try:
        confidence = float(confidence)
        if confidence > 1.0 and confidence <= 100.0:
            confidence = confidence / 100.0
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))
    reasoning = str(parsed.get("reasoning") or "").strip()
    return {
        "predicted_label": label if label in VALID_LABELS else "",
        "confidence": confidence,
        "reasoning": reasoning,
        "parse_ok": bool(label and label in VALID_LABELS),
        "error": "" if label in VALID_LABELS else "invalid_or_missing_label",
    }


def _call_openai_json_local(
    client: Any,
    *,
    model_name: str,
    prompt: str,
    temperature: float,
    max_retries: int = 5,
    base_sleep: float = 2.0,
) -> tuple[str, str]:
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
        except Exception as exc:  # noqa: BLE001
            last_error = f"{type(exc).__name__}: {exc}"
            message = str(exc).lower()
            if any(tok in message for tok in ("rate", "429", "timeout", "temporar")):
                time.sleep(base_sleep * (2**attempt))
            else:
                time.sleep(base_sleep * (attempt + 1))
    return "", last_error or "api_failure"


def _resolve_openai_helpers() -> tuple[Any, Any]:
    """Prefer research helpers when available; else use local fallbacks."""
    _ensure_paths()
    try:
        from llm_baseline import call_openai_json, parse_prediction

        return call_openai_json, parse_prediction
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "llm_baseline import failed (%s); using in-module OpenAI helpers",
            exc,
        )
        return _call_openai_json_local, _parse_prediction_local


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
    call_openai_json, parse_prediction = _resolve_openai_helpers()
    from openai import OpenAI

    started = time.perf_counter()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for the LLM pipeline")

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = _build_product_llm_prompt(text)
    # Cap consistency runs for product latency (keyword fallback often followed long timeouts).
    configured = max(1, int(settings.consistency_runs)) if settings.enable_confidence_calibration else 1
    n_runs = min(configured, 3)
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
            logger.warning("llm_pipeline API error run %s/%s: %s", i + 1, n_runs, api_error)
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
