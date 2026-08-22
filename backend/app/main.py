from contextlib import asynccontextmanager
import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import analyse, auth, chat, check_ins, health, privacy, transcription, uploads

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Ensure app loggers emit on Render (uvicorn may not attach handlers to app.*)."""
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(levelname)s:%(name)s:%(message)s",
            stream=sys.stdout,
        )
    logging.getLogger("app").setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Runs before requests are served. Failures here exit the process and look like
    # Render "Port scan timeout" if the exception is easy to miss in logs.
    _configure_logging()
    try:
        init_db()
    except Exception:
        logger.exception("Startup aborted: database init failed")
        raise
    yield


app = FastAPI(
    title="TrustMind AI API",
    description=(
        "Trustworthy wellbeing analysis for the TrustMind AI MSc dissertation.\n\n"
        "**Analyse:** `POST /api/v1/analyse` (alias `/api/analyse`).\n"
        "**Multimodal preprocess:** `/api/v1/transcribe`, `/api/v1/process-image`, "
        "`/api/v1/process-pdf`.\n"
        "Switch pipelines with `USE_RAG` in `.env`. "
        "See `/docs` for request/response examples including abstention."
    ),
    version="1.2.1",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(analyse.router)
app.include_router(transcription.router)
app.include_router(uploads.router)
app.include_router(check_ins.router)
app.include_router(chat.router)
app.include_router(privacy.router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "TrustMind AI backend is running",
        "docs": "/docs",
        "health": "/health",
        "version": "1.2.1",
    }
