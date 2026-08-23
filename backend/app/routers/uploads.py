"""Image and PDF preprocessing API routes."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from app.schemas.uploads import ImageProcessResponse, PdfProcessResponse
from app.services.file_validation_service import FileValidationError
from app.services.image_processing_service import (
    ImageProcessingError,
    process_image_bytes,
)
from app.services.pdf_processing_service import PdfProcessingError, process_pdf_bytes
from app.services.rate_limit import RateLimitExceeded, check_rate_limit

router = APIRouter(tags=["uploads"])


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host or "unknown"
    return "unknown"


@router.post(
    "/api/v1/process-image",
    response_model=ImageProcessResponse,
    summary="Process an uploaded image for contextual text",
)
@router.post(
    "/api/process-image",
    response_model=ImageProcessResponse,
    include_in_schema=True,
    summary="Process an uploaded image (alias)",
)
async def process_image(
    request: Request,
    file: UploadFile = File(..., description="JPEG, PNG, or WEBP image"),
) -> ImageProcessResponse:
    try:
        check_rate_limit(f"image:{_client_key(request)}")
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc

    data = await file.read()
    try:
        result = process_image_bytes(
            data=data,
            filename=file.filename,
            content_type=file.content_type,
        )
    except FileValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ImageProcessingError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    finally:
        await file.close()

    return ImageProcessResponse(**result)


@router.post(
    "/api/v1/process-pdf",
    response_model=PdfProcessResponse,
    summary="Extract text from an uploaded PDF",
)
@router.post(
    "/api/process-pdf",
    response_model=PdfProcessResponse,
    include_in_schema=True,
    summary="Extract text from an uploaded PDF (alias)",
)
async def process_pdf(
    request: Request,
    file: UploadFile = File(..., description="PDF document"),
) -> PdfProcessResponse:
    try:
        check_rate_limit(f"pdf:{_client_key(request)}")
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc

    data = await file.read()
    try:
        result = process_pdf_bytes(
            data=data,
            filename=file.filename,
            content_type=file.content_type,
        )
    except FileValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except PdfProcessingError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    finally:
        await file.close()

    return PdfProcessResponse(**result)
