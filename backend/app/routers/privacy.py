from fastapi import APIRouter, Depends

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.services.auth_service import delete_user_data
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/privacy", tags=["privacy"])


@router.delete("/me")
def delete_my_data(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    delete_user_data(db, user)
    return {"message": "Your account and associated data have been deleted"}
