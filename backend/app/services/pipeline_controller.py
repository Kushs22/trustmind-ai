"""
Analyse pipeline controller — chooses LLM vs RAG and applies trust safeguards.

Frontend never calls OpenAI directly; all analyse traffic goes through FastAPI.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from app.config import settings
from app.schemas.analyse import AnalyseRequest
from app.services.abstention import apply_abstention
from app.services.analyse_logging import log_analyse_run
from app.services.confidence_calibration import uncertainty_from_confidence
from app.services.evidence_presentation import (
    build_evidence_items,
    sanitise_reasoning,
)
from app.services.support_resources import get_support_resources
from app.services.trust_signals import (
    compute_trust_signals,
    prediction_display_name,
    resolve_grounding,
)

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "This tool provides wellbeing support information and should not be considered "
    "a medical diagnosis."
)
HUMAN_OVERSIGHT = (
    "This tool should not replace qualified healthcare professionals."
)
PRIVACY_NOTICE = (
    "No unnecessary storage of personal text, audio, images, or PDFs. "
    "Raw check-in content is only saved when you explicitly opt in and disable "
    "private mode. Uploaded files are deleted after processing in privacy mode "
    "and are never added to the trusted knowledge base."
)


@dataclass
class PipelineResult:
    """Unified analyse result for LLM and LLM+RAG modes."""

    status: str  # accepted | abstained
    prediction: str | None
    confidence: float
    reasoning: str
    sources: list[str] = field(default_factory=list)
    message: str = ""
    recommendation: str = ""
    pipeline_used: str = "LLM"
    support_resources: list[dict[str, str]] = field(default_factory=list)
    disclaimer: str = DISCLAIMER
    privacy_notice: str = PRIVACY_NOTICE
    human_oversight: str = HUMAN_OVERSIGHT
    concern_level: str = "Low"
    ai_confidence: str = "0%"
    uncertainty_level: str = "Medium"
    grounding_status: str = ""
    abstention_status: str = "Prediction accepted"
    explanation: str = ""
    safe_next_steps: list[str] = field(default_factory=list)
    safety_note: str = DISCLAIMER
    early_signs: list[str] = field(default_factory=list)
    potential_indicators: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    error: str = ""
    confidence_breakdown: dict[str, int] = field(default_factory=dict)
    uncertainty: str = ""
    prediction_display: str | None = None
    trust_signals: dict[str, Any] = field(default_factory=dict)
    grounding: dict[str, str] = field(default_factory=dict)
    evidence_used: list[dict[str, Any]] = field(default_factory=list)
    sources_detail: list[dict[str, Any]] = field(default_factory=list)
    safety_triggered: bool = False
    debug: dict[str, Any] | None = None


def _map_concern(prediction: str | None, abstained: bool) -> str:
    if abstained or not prediction:
        return "High" if abstained else "Low"
    key = prediction.lower()
    if key == "suicidewatch":
        return "High"
    if key in {"depression", "anxiety", "bipolar"}:
        return "Moderate"
    return "Low"


def _confidence_percent(confidence: float) -> str:
    pct = max(0, min(100, int(round(float(confidence) * 100))))
    return f"{pct}%"


def _default_next_steps(high_risk: bool) -> list[str]:
    if high_risk:
        return [
            "If you are in immediate danger, contact emergency services",
            "Reach out to Samaritans on 116 123 (UK)",
            "Speak to a trusted person or UWE wellbeing support",
        ]
    return [
        "Consider speaking to someone you trust",
        "Explore UWE wellbeing support if you are a student",
        "Contact professional support if feelings worsen",
    ]


def run_configured_pipeline(request: AnalyseRequest) -> PipelineResult:
    """
    Execute Mode A (LLM) or Mode B (RAG).

    Per-request `pipeline_mode` overrides the server `USE_RAG` default when set to
    llm or rag (auto keeps the env setting). Fallback order for RAG: RAG → LLM → keyword.
    """
    text = re.sub(r"\s+", " ", request.text).strip()
    if not text:
        raise ValueError("Text must not be empty")

    mode = (request.pipeline_mode or "auto").strip().lower()
    if mode == "llm":
        use_rag = False
    elif mode == "rag":
        use_rag = True
    else:
        use_rag = bool(settings.use_rag)

    if not settings.openai_api_key:
        logger.error("OPENAI_API_KEY is not set on the server — using keyword fallback")
        raw = _keyword_raw(text, error="OPENAI_API_KEY missing on server")
    else:
        raw: dict[str, Any] = {}
        error = ""
        try:
            if use_rag:
                from app.services.rag_pipeline_service import run_rag_pipeline

                raw = run_rag_pipeline(text)
            else:
                from app.services.llm_pipeline import run_llm_pipeline

                raw = run_llm_pipeline(text)
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"
            logger.exception("Primary pipeline failed (%s)", error)
            if use_rag:
                try:
                    from app.services.llm_pipeline import run_llm_pipeline

                    raw = run_llm_pipeline(text)
                    raw["error"] = f"rag_failed_then_llm: {error}"
                    logger.warning("RAG failed; served LLM-only response")
                except Exception as llm_exc:  # noqa: BLE001
                    error = f"{error} | llm_also_failed: {type(llm_exc).__name__}: {llm_exc}"
                    logger.exception("LLM fallback also failed")
                    raw = _keyword_raw(text, error=error)
            else:
                raw = _keyword_raw(text, error=error)

    prediction = raw.get("prediction")
    confidence = float(raw.get("confidence") or 0.0)
    reasoning = sanitise_reasoning(str(raw.get("reasoning") or ""))
    sources = list(raw.get("sources") or [])
    passages = list(raw.get("retrieved_passages") or [])
    if not settings.enable_source_display:
        sources = []

    decision = apply_abstention(confidence, text=text)
    abstained = decision.abstained
    final_prediction = None if abstained else prediction

    # Safety independent of confidence / RAG success
    support = get_support_resources(
        prediction=prediction,
        sources=sources,
        reasoning=reasoning,
        user_text=text,
    )
    high_risk = bool(support)

    concern = _map_concern(final_prediction, abstained)
    breakdown = dict(raw.get("confidence_breakdown") or {})
    uncertainty = str(raw.get("uncertainty") or "") or uncertainty_from_confidence(confidence)
    if abstained:
        uncertainty = uncertainty or "Very High"
    pipeline_used = str(raw.get("pipeline_used") or ("LLM+RAG" if use_rag else "LLM"))
    pipeline_error = str(raw.get("error") or "")

    calibrated_pct = int(round(confidence * 100)) if confidence <= 1.0 else int(round(confidence))
    is_standalone_llm = "RAG" not in pipeline_used.upper() and pipeline_used != "keyword_fallback"
    has_retrieval = "RAG" in pipeline_used.upper() and bool(passages)

    if is_standalone_llm:
        trust = compute_trust_signals(
            calibrated_pct=calibrated_pct,
            breakdown=breakdown or None,
            has_retrieval=False,
        )
        # Prefer resolve_grounding so this path never depends on a bare constructor import.
        grounding_info = resolve_grounding(
            pipeline_used="LLM",
            has_passages=False,
            trust=trust,
        )
        # Never present retrieval evidence in standalone LLM mode
        evidence_dicts: list[dict[str, Any]] = []
        shown_evidence: list[dict[str, Any]] = []
        sources = []
        passages = []
    else:
        trust = compute_trust_signals(
            calibrated_pct=calibrated_pct,
            breakdown=breakdown or None,
            has_retrieval=has_retrieval,
        )
        if "RAG" not in pipeline_used.upper():
            trust = compute_trust_signals(
                calibrated_pct=calibrated_pct,
                breakdown=breakdown or None,
                has_retrieval=False,
            )
        grounding_info = resolve_grounding(
            pipeline_used=pipeline_used,
            has_passages=bool(passages),
            trust=trust,
        )
        evidence_items = build_evidence_items(
            passages,
            user_text=text,
            prediction=final_prediction or prediction,
        )
        evidence_dicts = [e.to_dict() for e in evidence_items]
        if evidence_dicts and settings.enable_source_display:
            sources = [e["source_id"] for e in evidence_dicts]
        shown_evidence = []  # set below when not abstained

    pred_display = prediction_display_name(final_prediction)

    if abstained:
        abstention_status = "Abstention triggered — no clinical prediction"
        explanation = decision.message
        if grounding_info.status in {"limited", "ungrounded"}:
            explanation = (
                f"{decision.message} Retrieval provided limited or no supporting "
                f"evidence for a confident assessment."
            )
        grounding_status = grounding_info.label
        early_signs: list[str] = []
        potential_indicators: list[str] = []
        next_steps = [decision.recommendation] + _default_next_steps(high_risk)
        shown_evidence = []
    else:
        abstention_status = "Prediction accepted"
        explanation = reasoning or "Assessment completed."
        grounding_status = grounding_info.label
        if pipeline_used == "keyword_fallback" and pipeline_error:
            safe_err = re.sub(r"sk-[A-Za-z0-9_\-]+", "sk-***", pipeline_error)[:400]
            grounding_status = f"keyword_fallback ({safe_err})"
        early_signs = [final_prediction] if final_prediction else []
        potential_indicators = [pred_display] if pred_display else list(early_signs)
        next_steps = _default_next_steps(high_risk)
        if not is_standalone_llm:
            shown_evidence = evidence_dicts
        if "_keyword" in raw:
            kw = raw["_keyword"]
            early_signs = kw.early_signs
            potential_indicators = list(kw.early_signs)
            next_steps = kw.safe_next_steps
            explanation = kw.explanation
            concern = kw.concern_level

    public_message = decision.message if abstained else ""
    if pipeline_used == "keyword_fallback" and pipeline_error and not public_message:
        public_message = re.sub(r"sk-[A-Za-z0-9_\-]+", "sk-***", pipeline_error)[:400]

    debug: dict[str, Any] | None = None
    if getattr(request, "include_debug", False):
        debug = {
            "latency_ms": float(raw.get("latency_ms") or 0.0),
            "n_retrieved_chunks": len(passages),
            "openai_model": settings.openai_model,
            "embedding_model": "text-embedding-3-small",
            "confidence_threshold": settings.confidence_threshold,
            "grounding_retrieval_quality_min": settings.grounding_retrieval_quality_min,
            "grounding_evidence_strength_min": settings.grounding_evidence_strength_min,
            "pipeline_used": pipeline_used,
            "consistency_runs": settings.consistency_runs,
        }

    result = PipelineResult(
        status=decision.status,
        prediction=final_prediction,
        prediction_display=pred_display,
        confidence=confidence,
        reasoning=reasoning if not abstained else decision.message,
        sources=sources,
        message=public_message,
        recommendation=decision.recommendation if abstained else "",
        pipeline_used=pipeline_used,
        support_resources=support,
        concern_level=concern,
        ai_confidence=_confidence_percent(confidence),
        uncertainty_level=uncertainty,
        grounding_status=grounding_status,
        abstention_status=abstention_status,
        explanation=explanation,
        safe_next_steps=next_steps[:5],
        safety_note=f"{DISCLAIMER} {HUMAN_OVERSIGHT}",
        early_signs=early_signs,
        potential_indicators=potential_indicators,
        latency_ms=float(raw.get("latency_ms") or 0.0),
        error=pipeline_error,
        confidence_breakdown=breakdown,
        uncertainty=uncertainty,
        trust_signals=trust.to_dict(),
        grounding=grounding_info.to_dict(),
        evidence_used=shown_evidence,
        sources_detail=evidence_dicts,
        safety_triggered=high_risk,
        debug=debug,
    )

    log_analyse_run(
        {
            "pipeline_used": result.pipeline_used,
            "prediction": result.prediction,
            "confidence": result.confidence,
            "confidence_breakdown": result.confidence_breakdown,
            "trust_signals": result.trust_signals,
            "grounding": result.grounding,
            "uncertainty": result.uncertainty,
            "safety_triggered": result.safety_triggered,
            "llm_confidence_raw": raw.get("llm_confidence_raw"),
            "consistency_labels": raw.get("consistency_labels"),
            "calibration": raw.get("calibration"),
            "sources": result.sources,
            "abstained": abstained,
            "status": result.status,
            "latency_ms": result.latency_ms,
            "error": result.error,
            "text_chars": len(text),
            "use_rag": use_rag,
            "pipeline_mode": mode,
            "openai_configured": bool(settings.openai_api_key),
        }
    )
    return result


def _keyword_raw(text: str, *, error: str) -> dict:
    """Map keyword analysis into the shared pipeline payload shape."""
    from app.services.analyse_service import _run_keyword_analysis

    kw = _run_keyword_analysis(AnalyseRequest(text=text))
    conf = 0.5
    try:
        conf = float(str(kw.ai_confidence).replace("%", "")) / 100.0
    except ValueError:
        conf = 0.5
    return {
        "prediction": None,
        "confidence": conf,
        "reasoning": kw.explanation,
        "sources": [],
        "retrieved_passages": [],
        "pipeline_used": "keyword_fallback",
        "latency_ms": 0.0,
        "error": error,
        "parse_ok": False,
        "_keyword": kw,
    }
