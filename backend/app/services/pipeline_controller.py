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
from app.services.abstention import (
    LIMITED_CONFIDENCE_DISCLAIMER,
    apply_abstention,
    is_low_signal_checkin,
    is_underspecified_input,
    low_signal_invite_message,
    short_checkin_reflection,
    short_wellbeing_heuristic_label,
    strip_short_input_result_leaks,
)
from app.services.input_kind import (
    COACHING_WITH_FEELINGS_PREFIX,
    classify_input_kind,
    coaching_invite_result_fields,
)
from app.services.analyse_logging import log_analyse_run
from app.services.confidence_calibration import uncertainty_from_confidence
from app.services.evidence_presentation import (
    build_evidence_items,
    sanitise_reasoning,
)
from app.services.llm_provider import keyword_fallback_grounding_status
from app.services.support_resources import get_support_resources
from app.services.support_urgency import compute_support_urgency
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
    "Uploaded images and PDFs are processed ephemerally for analysis context "
    "only — binary files are not kept as a long-term vault and never enter the "
    "trusted knowledge base. Check-in text and conversation history are saved "
    "only when you opt in (and private mode can omit raw text from history)."
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
    support_urgency: int | None = None
    support_urgency_band: str | None = None
    support_urgency_rationale: str | None = None
    support_urgency_uncertain: bool = False
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
            "If you are in immediate danger, call 999 or go to A&E",
            "You can reach Samaritans on 116 123 (UK) any time — they're there to listen",
            "Please speak to someone you trust, or contact UWE wellbeing support",
        ]
    return [
        "If it helps, talk with someone you trust about how you're feeling",
        "Explore UWE wellbeing support if you are a student",
        "Reach out for professional support if things feel heavier or worsen",
    ]


def run_configured_pipeline(
    request: AnalyseRequest,
    *,
    continuity_context: str = "",
) -> PipelineResult:
    """
    Execute Mode A (LLM) or Mode B (RAG).

    Per-request `pipeline_mode` overrides the server `USE_RAG` default when set to
    llm or rag (auto keeps the env setting). Fallback order for RAG: RAG → LLM → keyword.
    Optional continuity_context is prior saved check-ins for pick-up-where-you-left-off.
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

    continuity = (continuity_context or "").strip()
    kind = classify_input_kind(text)

    # Pure coaching / "act as life coach" instructions without a personal story:
    # invite them to share — do not hard-fail into the abstention UI.
    if kind.coaching_without_story:
        raw = coaching_invite_result_fields()
    elif not settings.openai_api_key and not settings.gemini_api_key and not settings.groq_api_key:
        logger.error(
            "No LLM API key set (GROQ_API_KEY / GEMINI_API_KEY / OPENAI_API_KEY) — using keyword fallback"
        )
        raw = _keyword_raw(text, error="No LLM API key configured on server")
    else:
        raw: dict[str, Any] = {}
        error = ""
        try:
            if use_rag:
                from app.services.rag_pipeline_service import run_rag_pipeline

                raw = run_rag_pipeline(text, continuity_context=continuity)
            else:
                from app.services.llm_pipeline import run_llm_pipeline

                raw = run_llm_pipeline(text, continuity_context=continuity)
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"
            logger.exception("Primary pipeline failed (%s)", error)
            if use_rag:
                try:
                    from app.services.llm_pipeline import run_llm_pipeline

                    raw = run_llm_pipeline(text, continuity_context=continuity)
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

    # Coaching + feelings: keep classification, but acknowledge the guided-conversation ask.
    if (
        kind.is_coaching_request
        and kind.has_personal_story
        and reasoning
        and "share what" not in reasoning.lower()
        and COACHING_WITH_FEELINGS_PREFIX.lower() not in reasoning.lower()
    ):
        reasoning = f"{COACHING_WITH_FEELINGS_PREFIX}{reasoning}".strip()

    # Rich first-person emotional narrative with no label: prefer a safe theme over abstain.
    if not prediction and kind.rich_first_person:
        from app.services.input_kind import emotion_theme_heuristic

        heuristic = emotion_theme_heuristic(text)
        if heuristic:
            prediction = heuristic
            confidence = max(confidence, 0.58)
            if not reasoning:
                reasoning = short_checkin_reflection(heuristic, user_text=text)

    file_bits: list[str] = []
    for img in request.image_context or []:
        if img.included:
            file_bits.append((img.extracted_text or img.summary or "").strip())
    for pdf in request.pdf_context or []:
        if pdf.included:
            file_bits.append((pdf.extracted_text or pdf.summary or "").strip())
    file_text = " ".join(bit for bit in file_bits if bit)
    short_input = is_underspecified_input(
        typed_text=request.typed_text,
        speech_transcript=request.speech_transcript,
        file_text=file_text,
        combined_text=text,
    )
    user_probe = request.typed_text or request.speech_transcript or text
    low_signal = is_low_signal_checkin(user_probe) and not kind.coaching_without_story

    # Gibberish / no emotional content: soft invite — never invent a label or
    # fall through to a dead "Assessment completed." bubble.
    if low_signal:
        prediction = None
        confidence = min(float(confidence or 0.0), 0.3) or 0.2
        reasoning = low_signal_invite_message()
    # Short check-ins: ensure a usable label when cues are clear (LLM may omit one).
    elif short_input and not prediction:
        heuristic = short_wellbeing_heuristic_label(user_probe)
        if heuristic:
            prediction = heuristic
            if confidence < 0.55:
                confidence = 0.55
            if not reasoning or "matched a clear wellbeing cue" in reasoning.lower():
                reasoning = short_checkin_reflection(
                    heuristic,
                    user_text=user_probe,
                )
    elif short_input and prediction:
        # Prefer a warm short reflection over thin / lecture-y model copy.
        thin = len((reasoning or "").split()) < 18
        lecturey = any(
            p in (reasoning or "").lower()
            for p in (
                "shared only a little",
                "more you share",
                "matched a clear wellbeing cue",
                "for research classification",
            )
        )
        if thin or lecturey or not reasoning:
            reasoning = short_checkin_reflection(
                prediction,
                user_text=user_probe,
            )

    decision = apply_abstention(
        confidence,
        text=text,
        typed_text=request.typed_text,
        speech_transcript=request.speech_transcript,
        file_text=file_text,
        prediction=prediction,
    )
    abstained = decision.abstained
    final_prediction = None if abstained else prediction
    # Short-input tip lives under the prompt/input UI — never repeat it in results.
    reasoning = strip_short_input_result_leaks(reasoning)
    if (
        not abstained
        and decision.limited_confidence
        and final_prediction
        and LIMITED_CONFIDENCE_DISCLAIMER.lower() not in reasoning.lower()
    ):
        reasoning = f"{LIMITED_CONFIDENCE_DISCLAIMER} {reasoning}".strip()

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
        explanation = reasoning or low_signal_invite_message()
        grounding_status = grounding_info.label
        if pipeline_used == "keyword_fallback" and pipeline_error:
            logger.warning(
                "keyword_fallback grounding detail (not stored): %s",
                pipeline_error[:2000],
            )
            grounding_status = keyword_fallback_grounding_status(pipeline_error)
        early_signs = [final_prediction] if final_prediction else []
        potential_indicators = [pred_display] if pred_display else list(early_signs)
        next_steps = _default_next_steps(high_risk)
        if not is_standalone_llm:
            shown_evidence = evidence_dicts
        if "_keyword" in raw and not low_signal:
            kw = raw["_keyword"]
            early_signs = kw.early_signs
            potential_indicators = list(kw.early_signs)
            next_steps = kw.safe_next_steps
            explanation = kw.explanation
            concern = kw.concern_level
        if low_signal:
            early_signs = []
            potential_indicators = []
            explanation = reasoning or low_signal_invite_message()
            concern = "Low"

    explanation = strip_short_input_result_leaks(explanation)
    reasoning = strip_short_input_result_leaks(reasoning)
    if not explanation.strip():
        explanation = low_signal_invite_message()
    if not reasoning.strip():
        reasoning = explanation

    public_message = decision.message if abstained else ""
    if pipeline_used == "keyword_fallback" and pipeline_error and not public_message:
        err_l = pipeline_error.lower()
        if any(
            tok in err_l
            for tok in (
                "insufficient_quota",
                "credit_balance",
                "exceeded your current quota",
            )
        ):
            public_message = (
                "Full AI reflection is unavailable (provider credits/quota). "
                "Showing a basic English keyword check-in instead — "
                "set GROQ_API_KEY or a working GEMINI_MODEL on the server."
            )
        elif "404" in err_l or "not found" in err_l:
            public_message = (
                "The configured Gemini model was not found. "
                "Set GEMINI_MODEL=gemini-2.5-flash on Render, then redeploy."
            )
        else:
            public_message = (
                "Full AI reflection is temporarily unavailable. "
                "Showing a basic keyword check-in instead."
            )

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

    urgency = compute_support_urgency(
        safety_triggered=high_risk,
        concern_level=concern,
        confidence=confidence,
        status=decision.status,
        prediction=final_prediction or prediction,
        early_signs=early_signs,
        support_resources_present=bool(support),
    )

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
        support_urgency=urgency.score,
        support_urgency_band=urgency.band,
        support_urgency_rationale=urgency.rationale,
        support_urgency_uncertain=urgency.uncertain,
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
            "gemini_configured": bool(settings.gemini_api_key),
            "llm_provider": settings.llm_provider,
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
