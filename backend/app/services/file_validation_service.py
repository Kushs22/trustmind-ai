"""File size, MIME, and magic-byte validation for multimodal uploads."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import filetype

from app.config import settings


class FileValidationError(ValueError):
    """Raised when an uploaded file fails validation."""


# Magic-byte / filetype matches mapped to canonical MIME
_AUDIO_EXTS = {"webm", "mp4", "m4a", "mp3", "wav", "ogg"}
_IMAGE_EXTS = {"jpg", "jpeg", "png", "webp"}
_PDF_EXTS = {"pdf"}

# Signatures checked when filetype cannot detect (e.g. some webm)
_PDF_MAGIC = b"%PDF"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff"
_WEBP_RIFF = b"RIFF"
_WEBP_WEBP = b"WEBP"
_WAV_RIFF = b"RIFF"
_WAV_WAVE = b"WAVE"


@dataclass(frozen=True)
class ValidatedFile:
    safe_filename: str
    detected_mime: str
    size_bytes: int
    data: bytes


def sanitise_filename(name: str | None, *, default: str = "upload") -> str:
    raw = (name or default).strip() or default
    raw = Path(raw).name  # drop any path components
    raw = re.sub(r"[^\w.\-]+", "_", raw, flags=re.UNICODE)
    raw = raw[:120] or default
    if raw in {".", ".."}:
        return default
    return raw


def _detect_mime(data: bytes, claimed: str | None) -> str:
    kind = filetype.guess(data)
    if kind is not None:
        return kind.mime

    if data.startswith(_PDF_MAGIC):
        return "application/pdf"
    if data.startswith(_PNG_MAGIC):
        return "image/png"
    if data.startswith(_JPEG_MAGIC):
        return "image/jpeg"
    if len(data) >= 12 and data[:4] == _WEBP_RIFF and data[8:12] == _WEBP_WEBP:
        return "image/webp"
    if len(data) >= 12 and data[:4] == _WAV_RIFF and data[8:12] == _WAV_WAVE:
        return "audio/wav"
    # WebM / EBML
    if data.startswith(b"\x1a\x45\xdf\xa3"):
        return "audio/webm"
    # Ogg
    if data.startswith(b"OggS"):
        return "audio/ogg"
    # MP3 ID3 or frame sync
    if data.startswith(b"ID3") or (len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0):
        return "audio/mpeg"

    claimed_norm = (claimed or "").split(";")[0].strip().lower()
    # Do not trust browser-claimed MIME without a signature match.
    return "application/octet-stream"


def _bytes_limit_mb(mb: float) -> int:
    return int(float(mb) * 1024 * 1024)


def validate_upload(
    *,
    data: bytes,
    filename: str | None,
    claimed_content_type: str | None,
    category: str,
) -> ValidatedFile:
    """
    Validate an upload by size and file signature.

    category: "audio" | "image" | "pdf"
    """
    if not data:
        raise FileValidationError("Empty file upload.")

    size = len(data)
    if size > _bytes_limit_mb(settings.max_total_upload_mb):
        raise FileValidationError(
            f"File exceeds maximum total upload size of {settings.max_total_upload_mb} MB."
        )

    if category == "audio":
        max_mb = settings.max_audio_size_mb
        allowed = set(settings.allowed_audio_type_list)
    elif category == "image":
        max_mb = settings.max_image_size_mb
        allowed = set(settings.allowed_image_type_list)
    elif category == "pdf":
        max_mb = settings.max_pdf_size_mb
        allowed = set(settings.allowed_pdf_type_list)
    else:
        raise FileValidationError("Unsupported upload category.")

    if size > _bytes_limit_mb(max_mb):
        raise FileValidationError(f"File exceeds maximum size of {max_mb} MB.")

    detected = _detect_mime(data, claimed_content_type)
    # Normalise common aliases
    aliases = {
        "audio/x-wav": "audio/wav",
        "audio/wave": "audio/wav",
        "image/jpg": "image/jpeg",
    }
    detected = aliases.get(detected, detected)

    if detected not in allowed:
        raise FileValidationError(
            f"Unsupported or unrecognised file type ({detected}). "
            f"Allowed: {', '.join(sorted(allowed))}."
        )

    # Extra signature checks for category mismatch (e.g. exe renamed .jpg)
    if category == "pdf" and not data.startswith(_PDF_MAGIC):
        raise FileValidationError("File is not a valid PDF (signature check failed).")
    if category == "image":
        ok = (
            data.startswith(_PNG_MAGIC)
            or data.startswith(_JPEG_MAGIC)
            or (len(data) >= 12 and data[:4] == _WEBP_RIFF and data[8:12] == _WEBP_WEBP)
        )
        if not ok:
            raise FileValidationError("File is not a valid image (signature check failed).")
    if category == "audio":
        audio_ok = (
            data.startswith(b"\x1a\x45\xdf\xa3")  # webm/ebml
            or data.startswith(b"OggS")
            or data.startswith(b"ID3")
            or (len(data) >= 12 and data[:4] == _WAV_RIFF and data[8:12] == _WAV_WAVE)
            or (len(data) >= 8 and data[4:8] == b"ftyp")  # mp4 family
            or (len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0)
        )
        if not audio_ok:
            raise FileValidationError("File is not a valid audio file (signature check failed).")

    safe_name = sanitise_filename(filename)
    return ValidatedFile(
        safe_filename=safe_name,
        detected_mime=detected,
        size_bytes=size,
        data=data,
    )


def antivirus_scan_hook(_path: Path) -> list[str]:
    """
    Placeholder for future antivirus integration.

    Returns warnings; currently a no-op documented limitation.
    """
    return []
