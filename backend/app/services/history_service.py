import json
from datetime import UTC

from sqlalchemy.orm import Session

from app.models import CheckIn, User
from app.schemas.check_in import CheckInResponse, DashboardStatsResponse


def _format_date(dt) -> str:
    return dt.astimezone(UTC).strftime("%d %b %Y")


def _parse_confidence(value: str) -> int | None:
    digits = "".join(ch for ch in value if ch.isdigit())
    return int(digits) if digits else None


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
        )
        for row in rows
    ]


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
