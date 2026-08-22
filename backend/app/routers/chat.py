"""Ephemeral and saved chat follow-up endpoint."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_optional
from app.models import User
from app.schemas.analyse import SupportResourceOut
from app.schemas.check_in import (
    ChatFollowUpRequest,
    ChatFollowUpResponse,
    ChatMessageOut,
)
from app.services.conversation_service import (
    append_follow_up_to_check_in,
    generate_follow_up_reply,
    make_message,
    support_payload_if_needed,
)

router = APIRouter(tags=["chat"])


def _to_message_out(msg: dict) -> ChatMessageOut:
    return ChatMessageOut(
        role=msg["role"],
        content=msg["content"],
        created_at=msg.get("created_at"),
        safety_triggered=bool(msg.get("safety_triggered")),
    )


@router.post(
    "/api/v1/chat/follow-up",
    response_model=ChatFollowUpResponse,
    summary="Continue a wellbeing chat thread",
    description=(
        "Append a follow-up message. When `check_in_id` is set, the thread is "
        "loaded and persisted server-side (auth required). Otherwise `history` "
        "is used as ephemeral prompt context only."
    ),
)
def chat_follow_up(
    payload: ChatFollowUpRequest,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
) -> ChatFollowUpResponse:
    message = (payload.message or "").strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message cannot be empty.",
        )

    check_in_id = (payload.check_in_id or "").strip() or None
    if check_in_id:
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sign in to continue a saved check-in chat.",
            )
        try:
            _row, assistant_msg, messages = append_follow_up_to_check_in(
                db, user, check_in_id, message
            )
        except LookupError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        except PermissionError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        safety = bool(assistant_msg.get("safety_triggered"))
        return ChatFollowUpResponse(
            check_in_id=check_in_id,
            reply=assistant_msg["content"],
            safety_triggered=safety,
            support_resources=[
                SupportResourceOut(**r) for r in support_payload_if_needed(safety)
            ],
            messages=[_to_message_out(m) for m in messages],
            persisted=True,
        )

    prior = [
        {
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at,
            "safety_triggered": m.safety_triggered,
        }
        for m in (payload.history or [])
        if m.role in ("user", "assistant") and (m.content or "").strip()
    ]
    reply_text, safety = generate_follow_up_reply(
        user_message=message,
        prior_messages=prior,
    )
    user_msg = make_message("user", message)
    assistant_msg = make_message(
        "assistant",
        reply_text,
        safety_triggered=safety or None,
    )
    messages = prior + [user_msg, assistant_msg]
    return ChatFollowUpResponse(
        check_in_id=None,
        reply=reply_text,
        safety_triggered=safety,
        support_resources=[
            SupportResourceOut(**r) for r in support_payload_if_needed(safety)
        ],
        messages=[_to_message_out(m) for m in messages],
        persisted=False,
    )
