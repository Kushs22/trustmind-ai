import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models import CheckIn, User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse


def register_user(db: Session, payload: RegisterRequest) -> User:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise ValueError("An account with this email already exists")

    user = User(
        id=str(uuid.uuid4()),
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        is_anonymous=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, payload: LoginRequest) -> User | None:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user is None or user.hashed_password is None:
        return None
    if not verify_password(payload.password, user.hashed_password):
        return None
    return user


def create_anonymous_user(db: Session) -> User:
    user = User(
        id=str(uuid.uuid4()),
        email=None,
        hashed_password=None,
        is_anonymous=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def build_token_response(user: User) -> TokenResponse:
    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        is_anonymous=user.is_anonymous,
    )


def user_to_response(user: User) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, is_anonymous=user.is_anonymous)


def _iso(dt) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC).isoformat()
    return dt.astimezone(UTC).isoformat()


def _parse_json_field(raw: str | None) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


def export_user_data(db: Session, user: User) -> dict[str, Any]:
    """Build a portable JSON export of profile metadata + check-ins."""
    rows = (
        db.query(CheckIn)
        .filter(CheckIn.user_id == user.id)
        .order_by(CheckIn.created_at.asc())
        .all()
    )
    return {
        "exported_at": _iso(datetime.now(UTC)),
        "format_version": 1,
        "profile": {
            "id": user.id,
            "email": user.email,
            "is_anonymous": user.is_anonymous,
            "created_at": _iso(user.created_at),
        },
        "check_ins": [
            {
                "id": row.id,
                "created_at": _iso(row.created_at),
                "concern_level": row.concern_level,
                "ai_confidence": row.ai_confidence,
                "uncertainty_level": row.uncertainty_level,
                "grounding_status": row.grounding_status,
                "abstention_status": row.abstention_status,
                "explanation": row.explanation,
                "safe_next_steps": _parse_json_field(row.safe_next_steps),
                "safety_note": row.safety_note,
                "text_preview": row.text_preview,
                "is_private": row.is_private,
                "abstained": row.abstained,
                "support_urgency": row.support_urgency,
                "support_urgency_band": row.support_urgency_band,
                "support_urgency_rationale": row.support_urgency_rationale,
                "support_urgency_uncertain": bool(row.support_urgency_uncertain),
                "conversation": _parse_json_field(row.conversation_json),
            }
            for row in rows
        ],
    }


def delete_user_data(db: Session, user: User) -> None:
    """Cascade-delete the user and all check_ins (ORM relationship)."""
    db.delete(user)
    db.commit()
