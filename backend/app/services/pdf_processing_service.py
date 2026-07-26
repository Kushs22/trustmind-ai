"""PDF validation and text extraction (user context only — not RAG evidence)."""

from __future__ import annotations

import logging
import re
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PdfReadError

from app.config import settings
from app.services.file_validation_service import (
    FileValidationError,
    antivirus_scan_hook,
    validate_upload,
)
from app.utils.temp_file_manager import temporary_upload_dir

logger = logging.getLogger(__name__)


class PdfProcessingError(RuntimeError):
    pass


_PAGE_NUM_RE = re.compile(r"^\s*\d+\s*$")
_HEADER_FOOTER_RE = re.compile(r"^\s*(page\s+\d+(\s+of\s+\d+)?)\s*$", re.I)


def _clean_page_text(text: str) -> str:
    lines = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if _PAGE_NUM_RE.match(stripped):
            continue
        if _HEADER_FOOTER_RE.match(stripped):
            continue
        lines.append(stripped)
    return "\n".join(lines)


def _summarise(text: str, page_count: int) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return f"PDF with {page_count} page(s); no selectable text extracted."
    preview = cleaned[:280]
    if len(cleaned) > 280:
        preview += "…"
    return (
        f"User-provided PDF ({page_count} page(s)). Extracted text preview: {preview} "
        "This is contextual input only, not verified medical guidance."
    )


def process_pdf_bytes(
    *,
    data: bytes,
    filename: str | None,
    content_type: str | None,
) -> dict:
    validated = validate_upload(
        data=data,
        filename=filename,
        claimed_content_type=content_type,
        category="pdf",
    )

    with temporary_upload_dir(prefix="pdf_") as tmp_dir:
        path = tmp_dir / validated.safe_filename
        path.write_bytes(validated.data)
        warnings = list(antivirus_scan_hook(path))

        try:
            reader = PdfReader(BytesIO(validated.data))
        except PdfReadError as exc:
            raise PdfProcessingError("Malformed or unreadable PDF.") from exc

        if getattr(reader, "is_encrypted", False):
            try:
                # Empty password attempt; if still encrypted, reject
                ok = reader.decrypt("")  # type: ignore[arg-type]
                if ok == 0:
                    raise PdfProcessingError(
                        "This PDF is password-protected. Please upload an unlocked copy."
                    )
            except (FileNotDecryptedError, PdfProcessingError):
                raise PdfProcessingError(
                    "This PDF is password-protected. Please upload an unlocked copy."
                )
            except Exception as exc:  # noqa: BLE001
                raise PdfProcessingError(
                    "This PDF is password-protected. Please upload an unlocked copy."
                ) from exc

        page_count = len(reader.pages)
        if page_count > int(settings.max_pdf_pages):
            raise PdfProcessingError(
                f"PDF has {page_count} pages; maximum allowed is {settings.max_pdf_pages}."
            )

        page_texts: list[str] = []
        for page in reader.pages:
            try:
                raw = page.extract_text() or ""
            except Exception:  # noqa: BLE001
                raw = ""
            cleaned = _clean_page_text(raw)
            if cleaned:
                page_texts.append(cleaned)

        extracted = "\n\n".join(page_texts).strip()
        is_scanned = page_count > 0 and len(extracted) < 40

        if is_scanned:
            warnings.append(
                "This PDF appears scanned or has little selectable text."
            )
            if settings.enable_scanned_pdf_ocr:
                warnings.append(
                    "Scanned PDF OCR is enabled but page-image OCR is not run "
                    "in this request path; paste text or upload a text PDF."
                )
            else:
                warnings.append(
                    "OCR for scanned PDFs is disabled. Paste the text or upload a "
                    "PDF with selectable text."
                )

        safety_flags: list[str] = []
        low = extracted.lower()
        if any(k in low for k in ("suicid", "self-harm", "self harm", "kill myself")):
            safety_flags.append("crisis_language_in_pdf")

        summary = _summarise(extracted, page_count)
        logger.info(
            "pdf_processed filename=%s pages=%s extracted_chars=%s scanned=%s",
            validated.safe_filename,
            page_count,
            len(extracted),
            is_scanned,
        )
        return {
            "filename": validated.safe_filename,
            "page_count": page_count,
            "extracted_text": extracted,
            "document_summary": summary,
            "safety_flags": safety_flags,
            "warnings": warnings,
            "is_scanned": is_scanned,
        }
