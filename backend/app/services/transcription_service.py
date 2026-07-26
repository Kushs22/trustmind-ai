"""Configurable speech-to-text transcription (OpenAI Whisper by default)."""

from __future__ import annotations

import logging
from pathlib import Path

from app.config import settings
from app.services.file_validation_service import (
    FileValidationError,
    ValidatedFile,
    antivirus_scan_hook,
    validate_upload,
)
from app.utils.temp_file_manager import temporary_upload_dir

logger = logging.getLogger(__name__)


class TranscriptionError(RuntimeError):
    pass


def _extension_for_mime(mime: str) -> str:
    mapping = {
        "audio/webm": ".webm",
        "audio/mp4": ".mp4",
        "audio/mpeg": ".mp3",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/ogg": ".ogg",
    }
    return mapping.get(mime, ".webm")


def transcribe_audio_bytes(
    *,
    data: bytes,
    filename: str | None,
    content_type: str | None,
) -> dict:
    """
    Transcribe audio bytes. Temporary files are always deleted.

    Does not log raw audio or full transcripts unless enable_dev_content_logging.
    """
    validated = validate_upload(
        data=data,
        filename=filename,
        claimed_content_type=content_type,
        category="audio",
    )
    return _transcribe_validated(validated)


def _transcribe_validated(validated: ValidatedFile) -> dict:
    provider = (settings.transcription_provider or "openai").strip().lower()
    warnings: list[str] = []

    with temporary_upload_dir(prefix="audio_") as tmp_dir:
        suffix = _extension_for_mime(validated.detected_mime)
        path = tmp_dir / f"audio{suffix}"
        path.write_bytes(validated.data)
        warnings.extend(antivirus_scan_hook(path))

        try:
            if provider == "openai":
                result = _transcribe_openai(path, validated)
            else:
                raise TranscriptionError(
                    f"Unsupported transcription provider: {provider}"
                )
        finally:
            # directory cleanup handled by context manager
            pass

    if settings.enable_dev_content_logging:
        snippet = (result.get("transcript") or "")[:80]
        logger.info(
            "transcription_dev filename=%s chars=%s snippet=%r",
            validated.safe_filename,
            len(result.get("transcript") or ""),
            snippet,
        )
    else:
        logger.info(
            "transcription_ok filename=%s mime=%s bytes=%s chars=%s",
            validated.safe_filename,
            validated.detected_mime,
            validated.size_bytes,
            len(result.get("transcript") or ""),
        )

    result["warnings"] = list(result.get("warnings") or []) + warnings
    return result


def _transcribe_openai(path: Path, validated: ValidatedFile) -> dict:
    if not settings.openai_api_key:
        raise TranscriptionError("OPENAI_API_KEY is required for transcription.")

    from openai import OpenAI

    client = OpenAI(
        api_key=settings.openai_api_key,
        timeout=float(settings.transcription_timeout_seconds),
    )
    model = settings.transcription_model
    try:
        with path.open("rb") as audio_file:
            response = client.audio.transcriptions.create(
                model=model,
                file=audio_file,
                response_format="verbose_json",
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("transcription_failed err=%s", type(exc).__name__)
        raise TranscriptionError(
            "Transcription failed. Please try again or type your message instead."
        ) from exc

    transcript = (getattr(response, "text", None) or "").strip()
    language = getattr(response, "language", None) or "en"
    duration = getattr(response, "duration", None)
    warnings: list[str] = []
    if not transcript:
        warnings.append("Empty transcript returned from speech recognition.")

    # Soft duration check (browser also enforces)
    if duration is not None and float(duration) > float(settings.max_audio_duration_seconds):
        warnings.append(
            f"Recording exceeded {settings.max_audio_duration_seconds}s; "
            "consider shorter clips."
        )

    return {
        "status": "completed",
        "transcript": transcript,
        "language": str(language),
        "duration_seconds": float(duration) if duration is not None else None,
        "warnings": warnings,
    }
