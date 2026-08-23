"""Speech transcription API routes."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from app.schemas.transcription import TranscriptionResponse
from app.services.file_validation_service import FileValidationError
from app.services.rate_limit import RateLimitExceeded, enforce_rate_limit
from app.services.transcription_service import TranscriptionError, transcribe_audio_bytes

router = APIRouter(tags=["transcription"])


async def _transcribe_handler(
    request: Request,
    file: UploadFile,
) -> TranscriptionResponse:
    try:
        enforce_rate_limit(request, action="transcribe")
    except RateLimitExceeded as exc:
        headers = {}
        if exc.retry_after_seconds is not None:
            headers["Retry-After"] = str(exc.retry_after_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers=headers or None,
        ) from exc

    data = await file.read()
    try:
        result = transcribe_audio_bytes(
            data=data,
            filename=file.filename,
            content_type=file.content_type,
        )
    except FileValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except TranscriptionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    finally:
        await file.close()

    return TranscriptionResponse(**result)


@router.post(
    "/api/v1/transcribe",
    response_model=TranscriptionResponse,
    summary="Transcribe uploaded audio",
)
@router.post(
    "/api/transcribe",
    response_model=TranscriptionResponse,
    include_in_schema=True,
    summary="Transcribe uploaded audio (alias)",
)
async def transcribe(
    request: Request,
    file: UploadFile = File(..., description="Audio file (webm/mp4/mpeg/wav)"),
) -> TranscriptionResponse:
    return await _transcribe_handler(request, file)
