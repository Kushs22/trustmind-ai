"""
Analyse pipeline controller — chooses LLM vs RAG and applies trust safeguards.

Frontend never calls OpenAI directly; all analyse traffic goes through FastAPI.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from app.config import settings
from app.schemas.analyse import AnalyseRequest
from app.services.abstention import apply_abstention
from app.services.analyse_logging import log_analyse_run
from app.services.support_resources import get_support_resources

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "This tool provides wellbeing support information and should not be considered "
    "a medical diagnosis."
)
HUMAN_OVERSIGHT = (
    "This tool should not replace qualified healthcare professionals."
)
PRIVACY_NOTICE = (
    "No unnecessary storage of personal text. Raw check-in text is only saved when "
    "you explicitly opt in and disable private mode."
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
    # Legacy product fields (kept for dashboard / older UI pieces)
    concern_level: str = "Low"
    ai_confidence: str = "0%"
    uncertainty_level: str = "Medium"
    grounding_status: str = ""
    abstention_status: str = "Prediction accepted"
    explanation: str = ""
    safe_next_steps: list[str] = field(default_factory=list)
    safety_note: str = DISCLAIMER
    early_signs: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    error: str = ""


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
    Execute Mode A (LLM) or Mode B (RAG) based on settings.use_rag.

    Applies abstention and high-risk support resources after inference.
    Fallback order: RAG → LLM → keyword (never invents a SWMH label).
    """
    text = re.sub(r"\s+", " ", request.text).strip()
    if not text:
        raise ValueError("Text must not be empty")

    if not settings.openai_api_key:
        logger.error("OPENAI_API_KEY is not set on the server — using keyword fallback")
        raw = _keyword_raw(text, error="OPENAI_API_KEY missing on server")
    else:
        raw = {}
        error = ""
        try:
            if settings.use_rag:
                from app.services.rag_pipeline_service import run_rag_pipeline

                raw = run_rag_pipeline(text)
            else:
                from app.services.llm_pipeline import run_llm_pipeline

                raw = run_llm_pipeline(text)
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"
            logger.exception("Primary pipeline failed (%s)", error)
            # If RAG failed, try standalone LLM before keywords
            if settings.use_rag:
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
    reasoning = str(raw.get("reasoning") or "")
    sources = list(raw.get("sources") or [])
    if not settings.enable_source_display:
        sources = []

    decision = apply_abstention(confidence)
    abstained = decision.abstained

    final_prediction = None if abstained else prediction
    support = get_support_resources(
        prediction=prediction,
        sources=sources,
        reasoning=reasoning,
    )
    high_risk = bool(support)

    concern = _map_concern(final_prediction, abstained)
    uncertainty = "High" if abstained or confidence < 0.6 else ("Medium" if confidence < 0.85 else "Low")
    pipeline_used = str(raw.get("pipeline_used") or ("LLM+RAG" if settings.use_rag else "LLM"))
    pipeline_error = str(raw.get("error") or "")

    if abstained:
        abstention_status = "Abstention triggered — no clinical prediction"
        explanation = decision.message
        grounding = f"{pipeline_used} · abstained (confidence below threshold)"
        early_signs: list[str] = []
        next_steps = [decision.recommendation] + _default_next_steps(high_risk)
    else:
        abstention_status = "Prediction accepted"
        explanation = reasoning or "Assessment completed."
        grounding = (
            f"{pipeline_used} grounded assessment"
            + (f" using: {', '.join(sources[:5])}" if sources else "")
        )
        if pipeline_used == "keyword_fallback" and pipeline_error:
            # Truncate so we never leak secrets; enough to diagnose Render failures.
            safe_err = re.sub(r"sk-[A-Za-z0-9_\-]+", "sk-***", pipeline_error)[:400]
            grounding = f"keyword_fallback ({safe_err})"
        early_signs = [final_prediction] if final_prediction else []
        next_steps = _default_next_steps(high_risk)
        if "_keyword" in raw:
            kw = raw["_keyword"]
            early_signs = kw.early_signs
            next_steps = kw.safe_next_steps
            explanation = kw.explanation
            concern = kw.concern_level

    # Surface pipeline failures for ops/debug (no secrets; truncated above when set).
    public_message = decision.message if abstained else ""
    if pipeline_used == "keyword_fallback" and pipeline_error and not public_message:
        public_message = re.sub(r"sk-[A-Za-z0-9_\-]+", "sk-***", pipeline_error)[:400]

    result = PipelineResult(
        status=decision.status,
        prediction=final_prediction,
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
        grounding_status=grounding,
        abstention_status=abstention_status,
        explanation=explanation,
        safe_next_steps=next_steps[:5],
        safety_note=f"{DISCLAIMER} {HUMAN_OVERSIGHT}",
        early_signs=early_signs,
        latency_ms=float(raw.get("latency_ms") or 0.0),
        error=pipeline_error,
    )

    log_analyse_run(
        {
            "pipeline_used": result.pipeline_used,
            "prediction": result.prediction,
            "confidence": result.confidence,
            "sources": result.sources,
            "abstained": abstained,
            "status": result.status,
            "latency_ms": result.latency_ms,
            "error": result.error,
            "text_chars": len(text),
            "use_rag": settings.use_rag,
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
        "pipeline_used": "keyword_fallback",
        "latency_ms": 0.0,
        "error": error,
        "parse_ok": False,
        "_keyword": kw,
    }