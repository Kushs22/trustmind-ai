"""RAG classification pipeline wrapper (Mode B) for TrustMind analyse API."""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any

from app.config import settings
from app.services.confidence_calibration import (
    calibrate_confidence,
    majority_label,
)

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _ensure_paths() -> None:
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))


def run_rag_pipeline(text: str, continuity_context: str = "") -> dict[str, Any]:
    """
    Run hybrid BM25+FAISS retrieval then GPT classification.

    Applies multi-run consistency + calibrated confidence when enabled.
    Optional continuity_context is prior saved check-ins (server-loaded only).
    """
    _ensure_paths()
    research = _REPO_ROOT / "research"
    if str(research) not in sys.path:
        sys.path.insert(0, str(research))

    from app.services.llm_provider import complete_json, llm_configured
    from openai import OpenAI
    from rag.config import get_rag_config
    from rag.prompt_builder import build_rag_prompt
    from rag.rag_pipeline import RagPipeline, _parse_rag_response

    if not llm_configured():
        raise RuntimeError("OPENAI_API_KEY or GEMINI_API_KEY is required for the RAG pipeline")

    rag_cfg = get_rag_config()
    # Embeddings still use OpenAI when available; generation can fall back to Gemini.
    rag_cfg.openai_api_key = settings.openai_api_key or "unused"
    rag_cfg.gpt_model = settings.openai_model
    rag_cfg.temperature = settings.openai_temperature
    rag_cfg.top_k = settings.rag_top_k
    rag_cfg.use_rag = True

    passages: list[Any] = []
    retrieval_error = ""
    if settings.openai_api_key:
        client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=12.0,
        )
        pipeline = RagPipeline(rag_cfg, client=client)
        started = time.perf_counter()
        try:
            passages = pipeline.retriever.retrieve(text, top_k=settings.rag_top_k)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Retrieval failed in calibrated RAG path")
            passages = []
            retrieval_error = f"retrieval_error: {type(exc).__name__}: {exc}"
            # Exhausted OpenAI embeddings — continue with generation-only via free providers.
            if any(
                tok in str(exc).lower()
                for tok in (
                    "insufficient_quota",
                    "credit_balance",
                    "exceeded your current quota",
                    "429",
                )
            ):
                retrieval_error = "retrieval_skipped: openai_quota"
    else:
        started = time.perf_counter()
        retrieval_error = "retrieval_skipped: OPENAI_API_KEY missing (Gemini generation only)"

    prompt = build_rag_prompt(
        text,
        passages,
        continuity_context=continuity_context or "",
    )
    n_runs = max(1, int(settings.consistency_runs)) if settings.enable_confidence_calibration else 1
    consistency_temp = float(settings.consistency_temperature)
    primary_temp = float(settings.openai_temperature)

    runs: list[dict[str, Any]] = []
    api_errors: list[str] = []
    provider_used = ""
    for i in range(n_runs):
        temp = primary_temp if i == 0 else max(primary_temp, consistency_temp)
        response_text, api_error, provider = complete_json(
            system=(
                "You are a careful wellbeing research assistant. "
                "Respond with valid JSON only. "
                "LANGUAGE: write reasoning in the same language as the user's check-in."
            ),
            user=prompt,
            temperature=temp,
            max_tokens=800,
            openai_model=settings.openai_model,
            gemini_model=settings.gemini_model,
            groq_model=settings.groq_model,
        )
        if provider:
            provider_used = provider
        if api_error and not response_text:
            api_errors.append(api_error)
            continue
        parsed = _parse_rag_response(response_text or "")
        if api_error and not parsed.get("error"):
            parsed["error"] = api_error
        runs.append(parsed)
        logger.info(
            "rag_consistency_run i=%s/%s label=%s llm_conf=%.3f temp=%.2f provider=%s",
            i + 1,
            n_runs,
            parsed.get("predicted_label"),
            float(parsed.get("confidence") or 0.0),
            temp,
            provider_used or "?",
        )

    if not runs:
        error = retrieval_error or (api_errors[0] if api_errors else "empty_response")
        raise RuntimeError(error)

    labels = [r.get("predicted_label") or None for r in runs]
    prediction = majority_label(labels) or (runs[0].get("predicted_label") or None)
    # Prefer reasoning from a run that matches the majority label
    reasoning = ""
    llm_conf = float(runs[0].get("confidence") or 0.0)
    for r in runs:
        if (r.get("predicted_label") or "") == (prediction or "") or (
            str(r.get("predicted_label") or "").lower() == str(prediction or "").lower()
        ):
            reasoning = str(r.get("reasoning") or "")
            llm_conf = float(r.get("confidence") or 0.0)
            break
    if not reasoning:
        reasoning = str(runs[0].get("reasoning") or "")

    retrieved_meta = [p.to_dict() for p in passages]
    sources = list(runs[0].get("retrieved_sources") or [])
    if not sources and passages:
        sources = [p.source for p in passages]
    if settings.enable_source_display is False:
        sources = []

    if settings.enable_confidence_calibration:
        calibrated = calibrate_confidence(
            passages=retrieved_meta,
            prediction=prediction,
            llm_confidence=llm_conf,
            run_labels=labels,
            expected_k=settings.rag_top_k,
            has_retrieval=True,
        )
        confidence = calibrated.confidence
        breakdown = calibrated.breakdown.to_dict()
        uncertainty = calibrated.uncertainty
        calibration_log = calibrated.to_log_dict()
    else:
        confidence = llm_conf
        breakdown = {}
        uncertainty = ""
        calibration_log = {}

    latency_ms = (time.perf_counter() - started) * 1000.0
    error = retrieval_error or str(runs[0].get("error") or "")
    return {
        "prediction": prediction,
        "confidence": confidence,
        "reasoning": reasoning,
        "sources": sources,
        "pipeline_used": (
            f"LLM+RAG ({provider_used})" if provider_used else "LLM+RAG"
        ),
        "llm_provider": provider_used or "",
        "latency_ms": latency_ms,
        "error": error,
        "parse_ok": bool(prediction),
        "retrieved_passages": retrieved_meta,
        "confidence_breakdown": breakdown,
        "uncertainty": uncertainty,
        "calibration": calibration_log,
        "consistency_labels": labels,
        "llm_confidence_raw": llm_conf,
    }
