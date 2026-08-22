from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.check_in import (
    CheckInDetailResponse,
    CheckInResponse,
    DashboardStatsResponse,
)
from app.services.history_service import (
    dashboard_stats,
    delete_all_check_ins,
    get_check_in,
    list_check_ins,
)

router = APIRouter(prefix="/api/v1/check-ins", tags=["check-ins"])


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


@router.delete("")
def delete_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, int | str]:
    deleted = delete_all_check_ins(db, user)
    return {"deleted": deleted, "message": "Check-in history deleted"}
