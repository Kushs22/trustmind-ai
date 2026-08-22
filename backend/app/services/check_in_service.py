import json
import logging
import uuid

from sqlalchemy.orm import Session

from app.models import CheckIn, User
from app.schemas.analyse import (
    AnalyseDebugOut,
    AnalyseRequest,
    AnalyseResponse,
    ConfidenceBreakdownOut,
    EvidenceItemOut,
    GroundingOut,
    SupportResourceOut,
    TrustSignalsOut,
)
from app.schemas.multimodal import InputSummaryOut, ProcessedAttachmentOut
from app.services.analyse_service import run_analysis
from app.services.continuity_service import load_continuity_context

logger = logging.getLogger(__name__)


def _text_preview(text: str, max_len: int = 120) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3] + "..."


def analyse_and_optionally_save(
    db: Session,
    payload: AnalyseRequest,
    user: User | None,
) -> AnalyseResponse:
    continuity_context = load_continuity_context(db, user, payload)
    continuity_used = bool(continuity_context.strip())
    if continuity_used:
        logger.info(
            "Injecting continuity context for user_id=%s (%s chars)",
            getattr(user, "id", None),
            len(continuity_context),
        )
    result = run_analysis(payload, continuity_context=continuity_context)
    saved = False
    check_in_id: str | None = None

    # History stores only an approved preview of combined text — never original files.
    preview_source = (
        payload.typed_text
        or payload.text
        or payload.speech_transcript
        or result.explanation
        or ""
    )[:500]
    if payload.save_to_history:
        if user is None:
            raise PermissionError("Sign in or continue anonymously to save check-ins")

        check_in = CheckIn(
            id=str(uuid.uuid4()),
            user_id=user.id,
            concern_level=result.concern_level,
            ai_confidence=result.ai_confidence,
            uncertainty_level=result.uncertainty_level,
            grounding_status=result.grounding_status,
            abstention_status=result.abstention_status,
            explanation=result.explanation,
            safe_next_steps=json.dumps(result.safe_next_steps),
            safety_note=result.safety_note,
            text_preview=None
            if payload.analyse_privately
            else _text_preview(preview_source),
            is_private=payload.analyse_privately,
            abstained="abstention" in result.abstention_status.lower()
            or result.status == "abstained",
        )
        db.add(check_in)
        try:
            db.commit()
            db.refresh(check_in)
        except Exception:
            db.rollback()
            logger.exception(
                "Failed to save check-in for user_id=%s (save_to_history=True)",
                user.id,
            )
            raise
        saved = True
        check_in_id = check_in.id
        logger.info(
            "Saved check-in id=%s user_id=%s private=%s",
            check_in_id,
            user.id,
            payload.analyse_privately,
        )

    breakdown = None
    if result.confidence_breakdown:
        breakdown = ConfidenceBreakdownOut(**result.confidence_breakdown)

    trust = None
    if result.trust_signals:
        trust = TrustSignalsOut(**result.trust_signals)

    grounding = None
    if result.grounding:
        grounding = GroundingOut(**result.grounding)

    evidence = [EvidenceItemOut(**item) for item in (result.evidence_used or [])]
    sources_detail = [EvidenceItemOut(**item) for item in (result.sources_detail or [])]

    debug = None
    if result.debug:
        debug = AnalyseDebugOut(**result.debug)

    input_summary = None
    if result.input_summary:
        input_summary = InputSummaryOut(**result.input_summary)

    processed = [
        ProcessedAttachmentOut(**item) for item in (result.processed_attachments or [])
    ]

    return AnalyseResponse(
        id=check_in_id,
        status=result.status,
        prediction=result.prediction,
        prediction_display=result.prediction_display,
        confidence=result.confidence,
        reasoning=result.reasoning,
        sources=result.sources,
        message=result.message,
        recommendation=result.recommendation,
        pipeline_used=result.pipeline_used,
        support_resources=[SupportResourceOut(**r) for r in result.support_resources],
        disclaimer=result.disclaimer,
        privacy_notice=result.privacy_notice,
        human_oversight=result.human_oversight,
        concern_level=result.concern_level,
        ai_confidence=result.ai_confidence,
        uncertainty_level=result.uncertainty_level,
        grounding_status=result.grounding_status,
        abstention_status=result.abstention_status,
        explanation=result.explanation,
        safe_next_steps=result.safe_next_steps,
        safety_note=result.safety_note,
        early_signs=result.early_signs,
        potential_indicators=result.potential_indicators,
        saved_to_history=saved,
        continuity_used=continuity_used,
        confidence_breakdown=breakdown,
        uncertainty=result.uncertainty or result.uncertainty_level,
        trust_signals=trust,
        grounding=grounding,
        evidence_used=evidence,
        sources_detail=sources_detail,
        safety_triggered=result.safety_triggered,
        debug=debug,
        input_summary=input_summary,
        processed_attachments=processed,
    )
