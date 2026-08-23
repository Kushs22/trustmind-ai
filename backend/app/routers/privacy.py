from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.services.auth_service import delete_user_data, export_user_data

router = APIRouter(prefix="/api/v1/privacy", tags=["privacy"])


@router.get("/export")
def export_my_data(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    """Download profile metadata and all saved check-ins as JSON."""
    payload = export_user_data(db, user)
    return JSONResponse(
        content=payload,
        headers={
            "Content-Disposition": 'attachment; filename="trustmind-data-export.json"',
        },
    )


@router.delete("/me")
def delete_my_data(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Permanently delete the account and all associated check-ins."""
    delete_user_data(db, user)
    return {"message": "Your account and associated data have been deleted"}
