from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import analyse, auth, check_ins, health, privacy, transcription, uploads


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
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
    version="1.2.0",
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
app.include_router(privacy.router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "TrustMind AI backend is running",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0",
    }
