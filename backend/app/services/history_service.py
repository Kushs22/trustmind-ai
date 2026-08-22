import json
from datetime import UTC

from sqlalchemy.orm import Session

from app.models import CheckIn, User
from app.schemas.check_in import (
    ChatMessageOut,
    CheckInDetailResponse,
    CheckInResponse,
    DashboardStatsResponse,
)
from app.services.conversation_service import messages_for_row


def _format_date(dt) -> str:
    return dt.astimezone(UTC).strftime("%d %b %Y")


def _parse_confidence(value: str) -> int | None:
    digits = "".join(ch for ch in value if ch.isdigit())
    return int(digits) if digits else None


def _parse_next_steps(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return [raw] if raw.strip() else []
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    if isinstance(parsed, str) and parsed.strip():
        return [parsed.strip()]
    return []


def list_check_ins(db: Session, user: User) -> list[CheckInResponse]:
    rows = (
        db.query(CheckIn)
        .filter(CheckIn.user_id == user.id)
        .order_by(CheckIn.created_at.desc())
        .all()
    )
    return [
        CheckInResponse(
            id=row.id,
            date=_format_date(row.created_at),
            concern=row.concern_level,
            confidence=row.ai_confidence,
            abstained=row.abstained,
            preview=row.text_preview,
            is_private=row.is_private,
            created_at=row.created_at,
            support_urgency=row.support_urgency,
            support_urgency_band=row.support_urgency_band,
            support_urgency_uncertain=bool(row.support_urgency_uncertain),
        )
        for row in rows
    ]


def get_check_in(db: Session, user: User, check_in_id: str) -> CheckInDetailResponse | None:
    row = (
        db.query(CheckIn)
        .filter(CheckIn.id == check_in_id, CheckIn.user_id == user.id)
        .first()
    )
    if row is None:
        return None
    thread = messages_for_row(row)
    return CheckInDetailResponse(
        id=row.id,
        date=_format_date(row.created_at),
        concern=row.concern_level,
        confidence=row.ai_confidence,
        uncertainty_level=row.uncertainty_level,
        grounding_status=row.grounding_status,
        abstention_status=row.abstention_status,
        abstained=row.abstained,
        explanation=row.explanation or "",
        safe_next_steps=_parse_next_steps(row.safe_next_steps),
        safety_note=row.safety_note or "",
        preview=row.text_preview,
        is_private=row.is_private,
        created_at=row.created_at,
        support_urgency=row.support_urgency,
        support_urgency_band=row.support_urgency_band,
        support_urgency_rationale=row.support_urgency_rationale,
        support_urgency_uncertain=bool(row.support_urgency_uncertain),
        messages=[
            ChatMessageOut(
                role=m["role"],
                content=m["content"],
                created_at=m.get("created_at"),
                safety_triggered=bool(m.get("safety_triggered")),
            )
            for m in thread
        ],
    )


def dashboard_stats(db: Session, user: User) -> DashboardStatsResponse:
    rows = db.query(CheckIn).filter(CheckIn.user_id == user.id).all()
    confidences = [_parse_confidence(row.ai_confidence) for row in rows]
    valid = [value for value in confidences if value is not None]
    avg = round(sum(valid) / len(valid)) if valid else None

    return DashboardStatsResponse(
        saved_analyses=len(rows),
        avg_ai_confidence=avg,
        abstention_count=sum(1 for row in rows if row.abstained),
        privacy_mode="Active",
    )


def delete_all_check_ins(db: Session, user: User) -> int:
    count = db.query(CheckIn).filter(CheckIn.user_id == user.id).delete()
    db.commit()
    return count
