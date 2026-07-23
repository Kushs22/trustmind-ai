from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, object]:
    """Liveness + safe config diagnostics (no secrets)."""
    return {
        "status": "ok",
        "service": "trustmind-ai-backend",
        "version": "1.1.0",
        "openai_configured": bool(settings.openai_api_key),
        "use_rag": settings.use_rag,
        "enable_abstention": settings.enable_abstention,
        "analyse_backend": settings.analyse_backend,
    }
