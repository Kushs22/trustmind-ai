"""Standalone LLM classification pipeline (Mode A) for TrustMind analyse API."""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_RESEARCH = _REPO_ROOT / "research"


def _ensure_paths() -> None:
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))
    if str(_RESEARCH) not in sys.path:
        sys.path.insert(0, str(_RESEARCH))


def run_llm_pipeline(text: str) -> dict[str, Any]:
    """
    Run GPT-only wellbeing classification (no retrieval).

    Reuses research/llm_baseline helpers for fair dissertation parity.
    """
    _ensure_paths()
    from llm_baseline import build_prompt, call_openai_json, parse_prediction
    from openai import OpenAI

    started = time.perf_counter()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for the LLM pipeline")

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = build_prompt(text)
    response_text, api_error = call_openai_json(
        client,
        model_name=settings.openai_model,
        prompt=prompt,
        temperature=settings.openai_temperature,
    )
    if api_error and not response_text:
        raise RuntimeError(api_error)

    parsed = parse_prediction(response_text)
    latency_ms = (time.perf_counter() - started) * 1000.0
    return {
        "prediction": parsed["predicted_label"] or None,
        "confidence": float(parsed["confidence"]),
        "reasoning": parsed["reasoning"],
        "sources": [],
        "pipeline_used": "LLM",
        "latency_ms": latency_ms,
        "error": parsed.get("error") or "",
        "parse_ok": parsed.get("parse_ok", False),
    }
