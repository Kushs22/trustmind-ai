"""Image validation, EXIF stripping, and non-diagnostic context extraction."""

from __future__ import annotations

import base64
import io
import json
import logging
from typing import Any

from PIL import Image, ImageFile

from app.config import settings
from app.services.file_validation_service import (
    FileValidationError,
    antivirus_scan_hook,
    validate_upload,
)
from app.utils.temp_file_manager import temporary_upload_dir

# Avoid decompression-bomb crashes; we also enforce settings.max_image_pixels at runtime.
Image.MAX_IMAGE_PIXELS = 25_000_000
ImageFile.LOAD_TRUNCATED_IMAGES = False

logger = logging.getLogger(__name__)


class ImageProcessingError(RuntimeError):
    pass


IMAGE_SYSTEM_PROMPT = """You analyse user-uploaded images that may contain wellbeing-related written content.

Rules (strict):
- Describe only clearly visible content.
- Prefer extracting readable text (journals, notes, screenshots, leaflets, questionnaires, timetables).
- Do NOT infer a medical, psychiatric, or physical diagnosis.
- Do NOT infer hidden mental states from appearance alone.
- Do NOT identify people by name.
- Do NOT infer sensitive attributes (ethnicity, religion, disability, etc.).
- Do NOT make claims based on facial expression alone.
- Do NOT provide injury severity assessments.
- If the image shows injuries, medication packaging, medical reports, faces/bodies, or self-harm content:
  set safety_flags accordingly and keep descriptions minimal (no graphic detail).
- If the image is unrelated (e.g. a laptop photo with no wellbeing text), set useful_context to false
  and explain briefly that it does not provide useful wellbeing context.
- Refer urgent concerns to professional support; never diagnose.

Return ONLY valid JSON:
{
  "summary": "short non-diagnostic description",
  "extracted_text": "visible text if any",
  "contains_text": true,
  "useful_context": true,
  "safety_flags": [],
  "warnings": []
}
"""


def _strip_exif_and_reencode(data: bytes, mime: str) -> tuple[bytes, str]:
    """Load image, enforce dimension/pixel limits, strip EXIF, re-encode."""
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.load()
            width, height = img.size
            if width > settings.max_image_dimension or height > settings.max_image_dimension:
                raise ImageProcessingError(
                    f"Image dimensions exceed {settings.max_image_dimension}px limit."
                )
            pixels = width * height
            if pixels > settings.max_image_pixels:
                raise ImageProcessingError("Image exceeds maximum pixel limit.")

            # Convert to RGB for JPEG; keep PNG/WEBP as appropriate
            if mime == "image/png":
                out_format = "PNG"
                out_mime = "image/png"
                cleaned = img.convert("RGBA") if img.mode in ("P", "RGBA") else img.convert("RGB")
            elif mime == "image/webp":
                out_format = "WEBP"
                out_mime = "image/webp"
                cleaned = img.convert("RGB")
            else:
                out_format = "JPEG"
                out_mime = "image/jpeg"
                cleaned = img.convert("RGB")

            # Drop EXIF by not copying info
            buf = io.BytesIO()
            save_kwargs: dict[str, Any] = {}
            if out_format == "JPEG":
                save_kwargs["quality"] = 90
                save_kwargs["optimize"] = True
            cleaned.save(buf, format=out_format, **save_kwargs)
            return buf.getvalue(), out_mime
    except ImageProcessingError:
        raise
    except Image.DecompressionBombError as exc:
        raise ImageProcessingError("Image rejected (possible decompression bomb).") from exc
    except Exception as exc:  # noqa: BLE001
        raise ImageProcessingError("Corrupted or unreadable image.") from exc


def _heuristic_safety_flags(text: str, summary: str) -> list[str]:
    blob = f"{text} {summary}".lower()
    flags: list[str] = []
    if any(k in blob for k in ("self-harm", "self harm", "suicid", "cut myself", "hurt myself")):
        flags.append("possible_self_harm_content")
    if any(k in blob for k in ("injury", "bleeding", "wound", "bruise")):
        flags.append("possible_injury_image")
    if any(k in blob for k in ("medication", "prescription", "tablet", "pill bottle")):
        flags.append("possible_medication_image")
    if any(k in blob for k in ("face", "portrait", "person visible", "body")):
        flags.append("possible_person_image")
    return flags


def process_image_bytes(
    *,
    data: bytes,
    filename: str | None,
    content_type: str | None,
) -> dict:
    validated = validate_upload(
        data=data,
        filename=filename,
        claimed_content_type=content_type,
        category="image",
    )

    with temporary_upload_dir(prefix="img_") as tmp_dir:
        try:
            cleaned_bytes, out_mime = _strip_exif_and_reencode(
                validated.data, validated.detected_mime
            )
            path = tmp_dir / validated.safe_filename
            path.write_bytes(cleaned_bytes)
            warnings = antivirus_scan_hook(path)

            vision = _call_vision(cleaned_bytes, out_mime, validated.safe_filename)
            extracted = str(vision.get("extracted_text") or "").strip()
            summary = str(vision.get("summary") or "").strip()
            contains_text = bool(vision.get("contains_text")) or bool(extracted)
            useful = vision.get("useful_context", True)
            if useful is None:
                useful = True
            safety_flags = list(vision.get("safety_flags") or [])
            safety_flags.extend(_heuristic_safety_flags(extracted, summary))
            # Dedupe
            safety_flags = sorted(set(safety_flags))
            warnings = list(warnings) + list(vision.get("warnings") or [])

            if not useful and not extracted:
                warnings.append(
                    "This image does not appear to provide useful wellbeing context."
                )

            logger.info(
                "image_processed filename=%s contains_text=%s safety_flags=%s",
                validated.safe_filename,
                contains_text,
                len(safety_flags),
            )
            return {
                "filename": validated.safe_filename,
                "summary": summary,
                "extracted_text": extracted,
                "contains_text": contains_text,
                "safety_flags": safety_flags,
                "warnings": warnings,
                "useful_context": bool(useful),
            }
        finally:
            pass  # tmp_dir cleanup


def _call_vision(image_bytes: bytes, mime: str, filename: str) -> dict:
    if not settings.openai_api_key:
        # Offline-safe fallback: no vision — return empty extract with warning
        return {
            "summary": "Image received but vision processing is unavailable (API key not configured).",
            "extracted_text": "",
            "contains_text": False,
            "useful_context": False,
            "safety_flags": [],
            "warnings": ["Vision processing unavailable; image text was not extracted."],
        }

    from openai import OpenAI

    client = OpenAI(
        api_key=settings.openai_api_key,
        timeout=float(settings.image_processing_timeout_seconds),
    )
    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime};base64,{b64}"
    try:
        response = client.chat.completions.create(
            model=settings.image_processing_model,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": IMAGE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Analyse this uploaded image ({filename}) for wellbeing-related written context only.",
                        },
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
        )
        raw = response.choices[0].message.content or "{}"
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ImageProcessingError("Unexpected vision response.")
        return parsed
    except ImageProcessingError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("vision_failed err=%s", type(exc).__name__)
        raise ImageProcessingError(
            "Image processing failed. You can still type or speak your message."
        ) from exc
