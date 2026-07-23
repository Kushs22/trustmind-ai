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
    """
    text = re.sub(r"\s+", " ", request.text).strip()
    if not text:
        raise ValueError("Text must not be empty")

    raw: dict = {}
    error = ""
    try:
        if settings.use_rag:
            from app.services.rag_pipeline_service import run_rag_pipeline

            raw = run_rag_pipeline(text)
        else:
            from app.services.llm_pipeline import run_llm_pipeline

            raw = run_llm_pipeline(text)
    except Exception as exc:  # noqa: BLE001 — surface controlled fallback
        logger.exception("Primary pipeline failed; attempting keyword fallback")
        error = f"{type(exc).__name__}: {exc}"
        from app.services.analyse_service import _run_keyword_analysis

        kw = _run_keyword_analysis(AnalyseRequest(text=text))
        # Map keyword path into pipeline shape
        conf = 0.5
        try:
            conf = float(str(kw.ai_confidence).replace("%", "")) / 100.0
        except ValueError:
            conf = 0.5
        prediction = None
        if kw.early_signs:
            # Non-SWMH fallback — keep prediction null; use early signs only
            prediction = None
        raw = {
            "prediction": prediction,
            "confidence": conf,
            "reasoning": kw.explanation,
            "sources": [],
            "pipeline_used": "keyword_fallback",
            "latency_ms": 0.0,
            "error": error,
            "parse_ok": False,
            "_keyword": kw,
        }

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
        early_signs = [final_prediction] if final_prediction else []
        next_steps = _default_next_steps(high_risk)
        if "_keyword" in raw:
            kw = raw["_keyword"]
            early_signs = kw.early_signs
            next_steps = kw.safe_next_steps
            explanation = kw.explanation
            concern = kw.concern_level

    result = PipelineResult(
        status=decision.status,
        prediction=final_prediction,
        confidence=confidence,
        reasoning=reasoning if not abstained else decision.message,
        sources=sources,
        message=decision.message if abstained else "",
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
        error=str(raw.get("error") or error),
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
        }
    )
    return result
