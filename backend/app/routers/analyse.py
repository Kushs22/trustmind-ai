from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_optional
from app.models import User
from app.schemas.analyse import AnalyseRequest, AnalyseResponse
from app.services.check_in_service import analyse_and_optionally_save

router = APIRouter(prefix="/api/v1", tags=["analyse"])


@router.post("/analyse", response_model=AnalyseResponse)
def analyse(
    payload: AnalyseRequest,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
) -> AnalyseResponse:
    try:
        return analyse_and_optionally_save(db, payload, user)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
