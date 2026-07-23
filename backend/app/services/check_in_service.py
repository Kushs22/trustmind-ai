import json
import uuid

from sqlalchemy.orm import Session

from app.models import CheckIn, User
from app.schemas.analyse import AnalyseRequest, AnalyseResponse, SupportResourceOut
from app.services.analyse_service import run_analysis


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
    result = run_analysis(payload)
    saved = False
    check_in_id: str | None = None

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
            text_preview=None if payload.analyse_privately else _text_preview(payload.text),
            is_private=payload.analyse_privately,
            abstained="abstention" in result.abstention_status.lower()
            or result.status == "abstained",
        )
        db.add(check_in)
        db.commit()
        db.refresh(check_in)
        saved = True
        check_in_id = check_in.id

    return AnalyseResponse(
        id=check_in_id,
        status=result.status,
        prediction=result.prediction,
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
        saved_to_history=saved,
    )
