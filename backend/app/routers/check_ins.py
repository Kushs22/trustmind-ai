from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.database import get_db
from app.models import User
from app.schemas.check_in import CheckInResponse, DashboardStatsResponse
from app.services.history_service import (
    dashboard_stats,
    delete_all_check_ins,
    list_check_ins,
)
from sqlalchemy.orm import Session

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


@router.delete("")
def delete_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, int | str]:
    deleted = delete_all_check_ins(db, user)
    return {"deleted": deleted, "message": "Check-in history deleted"}
