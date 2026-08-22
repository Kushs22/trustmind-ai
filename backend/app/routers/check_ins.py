from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.analyse import SupportResourceOut
from app.schemas.check_in import (
    ChatFollowUpRequest,
    ChatFollowUpResponse,
    ChatMessageOut,
    CheckInDetailResponse,
    CheckInResponse,
    DashboardStatsResponse,
)
from app.services.conversation_service import (
    append_follow_up_to_check_in,
    support_payload_if_needed,
)
from app.services.history_service import (
    dashboard_stats,
    delete_all_check_ins,
    get_check_in,
    list_check_ins,
)

router = APIRouter(prefix="/api/v1/check-ins", tags=["check-ins"])


def _to_message_out(msg: dict) -> ChatMessageOut:
    return ChatMessageOut(
        role=msg["role"],
        content=msg["content"],
        created_at=msg.get("created_at"),
        safety_triggered=bool(msg.get("safety_triggered")),
    )


@router.get("", response_model=list[CheckInResponse])
def get_check_ins(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CheckInResponse]:
    return list_check_ins(db, user)


@router.get("/stats", response_model=DashboardStatsResponse)
def get_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DashboardStatsResponse:
    return dashboard_stats(db, user)


@router.get("/{check_in_id}", response_model=CheckInDetailResponse)
def get_check_in_detail(
    check_in_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CheckInDetailResponse:
    detail = get_check_in(db, user, check_in_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Check-in not found",
        )
    return detail


@router.post(
    "/{check_in_id}/messages",
    response_model=ChatFollowUpResponse,
    summary="Continue a saved check-in chat thread",
)
def post_check_in_message(
    check_in_id: str,
    payload: ChatFollowUpRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChatFollowUpResponse:
    try:
        _row, assistant_msg, messages = append_follow_up_to_check_in(
            db,
            user,
            check_in_id,
            payload.message,
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


@router.delete("")
def delete_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, int | str]:
    deleted = delete_all_check_ins(db, user)
    return {"deleted": deleted, "message": "Check-in history deleted"}
