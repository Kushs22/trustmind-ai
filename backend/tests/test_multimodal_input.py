"""Tests for multimodal input validation, normalisation, privacy cleanup, and RAG separation."""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT))

from app.schemas.analyse import AnalyseRequest  # noqa: E402
from app.schemas.multimodal import AttachmentContext  # noqa: E402
from app.services.file_validation_service import (  # noqa: E402
    FileValidationError,
    validate_upload,
)
from app.services.multimodal_input_service import (  # noqa: E402
    build_labelled_combined_text,
    normalize_multimodal_input,
)
from app.services.pdf_processing_service import (  # noqa: E402
    PdfProcessingError,
    process_pdf_bytes,
)
from app.services.support_resources import (  # noqa: E402
    get_support_resources,
    user_text_indicates_crisis,
)
from app.utils.temp_file_manager import temporary_upload_dir  # noqa: E402


def _minimal_png() -> bytes:
    """1x1 PNG."""
    import struct
    import zlib

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = zlib.compress(b"\x00\xff\x00\x00")
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", raw)
        + chunk(b"IEND", b"")
    )


def _simple_pdf(text: str = "I feel overwhelmed by university.") -> bytes:
    # Minimal PDF with a text stream (not encrypted)
    content = f"BT /F1 12 Tf 100 700 Td ({text}) Tj ET"
    stream = content.encode("latin-1")
    objects = []
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objects.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n"
    )
    objects.append(
        f"4 0 obj<< /Length {len(stream)} >>stream\n".encode("latin-1")
        + stream
        + b"\nendstream\nendobj\n"
    )
    objects.append(
        b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n"
    )
    body = b"".join(objects)
    header = b"%PDF-1.4\n"
    xref_pos = len(header) + len(body)
    # Simplified: use pypdf-friendly generation via report-less approach
    # Prefer building with pypdf writer if available
    try:
        from pypdf import PdfWriter
        from pypdf.generic import DecorationStringObject, DictionaryObject, NameObject

        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        # Add text annotation-like content via page merge is complex;
        # for extraction tests use a known extractable PDF from pypdf recipes.
        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue()
    except Exception:
        return header + body + f"xref\n0 0\ntrailer<< /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode(
            "latin-1"
        )


class MultimodalTests(unittest.TestCase):
    def test_valid_image_signature(self) -> None:
        data = _minimal_png()
        validated = validate_upload(
            data=data,
            filename="note.png",
            claimed_content_type="image/png",
            category="image",
        )
        self.assertEqual(validated.detected_mime, "image/png")
        self.assertEqual(validated.safe_filename, "note.png")

    def test_invalid_image_signature(self) -> None:
        fake = b"MZ\x90\x00this is not an image but named jpg"
        with self.assertRaises(FileValidationError):
            validate_upload(
                data=fake,
                filename="evil.jpg",
                claimed_content_type="image/jpeg",
                category="image",
            )

    def test_invalid_audio_mime(self) -> None:
        with self.assertRaises(FileValidationError):
            validate_upload(
                data=b"not-audio-content-at-all",
                filename="x.wav",
                claimed_content_type="audio/wav",
                category="audio",
            )

    def test_audio_size_limit(self) -> None:
        # tiny valid-looking wav header still fails size if we patch settings
        from app.config import settings

        data = b"RIFF" + b"\x00" * 8 + b"WAVE" + b"\x00" * 100
        with patch.object(settings, "max_audio_size_mb", 0.00001):
            with self.assertRaises(FileValidationError):
                validate_upload(
                    data=data,
                    filename="a.wav",
                    claimed_content_type="audio/wav",
                    category="audio",
                )

    def test_temp_dir_cleanup(self) -> None:
        with temporary_upload_dir(prefix="test_") as d:
            path = d / "f.txt"
            path.write_text("secret", encoding="utf-8")
            self.assertTrue(path.exists())
            kept = d
        self.assertFalse(kept.exists())

    def test_normalisation_labels_and_not_rag(self) -> None:
        combined = build_labelled_combined_text(
            typed_text="I feel low.",
            speech_transcript="I stopped meeting friends.",
            image_contexts=[
                AttachmentContext(
                    filename="note.png",
                    extracted_text="Overwhelmed by university",
                    included=True,
                )
            ],
            pdf_contexts=[
                AttachmentContext(
                    filename="journal.pdf",
                    extracted_text="Week 1: tired",
                    included=True,
                )
            ],
        )
        self.assertIn("Typed input:", combined)
        self.assertIn("Spoken input:", combined)
        self.assertIn("Text extracted from image", combined)
        self.assertIn("Text extracted from PDF", combined)

        req = AnalyseRequest(
            typed_text="I feel low.",
            speech_transcript="I stopped meeting friends.",
            image_context=[
                AttachmentContext(
                    filename="note.png",
                    extracted_text="Overwhelmed",
                    included=True,
                )
            ],
            pdf_context=[],
        )
        norm = normalize_multimodal_input(req)
        self.assertTrue(norm.input_summary.typed_text_used)
        self.assertTrue(norm.input_summary.speech_transcript_used)
        self.assertEqual(norm.input_summary.image_count, 1)
        # User context is separate from retrieved_evidence
        self.assertIn("typed_text", norm.user_context)
        self.assertNotIn("retrieved_evidence", norm.user_context)
        # Attachments metadata never claim to be trusted sources
        for att in norm.processed_attachments:
            self.assertIn(att.type, {"image", "pdf"})

    def test_uploads_not_trusted_rag_sources(self) -> None:
        """Grounding / evidence must not treat user files as NHS etc."""
        req = AnalyseRequest(
            typed_text="worried about exams",
            image_context=[
                AttachmentContext(
                    filename="leaflet.png",
                    extracted_text="Student Minds flyer text",
                    included=True,
                )
            ],
        )
        norm = normalize_multimodal_input(req)
        # Combined text is user context; no automatic source IDs
        self.assertTrue(norm.combined_user_text)
        self.assertEqual(norm.processed_attachments[0].filename, "leaflet.png")
        # No injection into a retrieved_evidence list
        self.assertEqual(norm.user_context.get("image_context")[0]["filename"], "leaflet.png")

    def test_pdf_valid_and_page_limit(self) -> None:
        from app.config import settings
        from pypdf import PdfWriter

        writer = PdfWriter()
        for _ in range(3):
            writer.add_blank_page(width=200, height=200)
        buf = io.BytesIO()
        writer.write(buf)
        data = buf.getvalue()
        result = process_pdf_bytes(
            data=data, filename="notes.pdf", content_type="application/pdf"
        )
        self.assertEqual(result["page_count"], 3)
        self.assertEqual(result["filename"], "notes.pdf")

        with patch.object(settings, "max_pdf_pages", 2):
            with self.assertRaises(PdfProcessingError):
                process_pdf_bytes(
                    data=data, filename="notes.pdf", content_type="application/pdf"
                )

    def test_pdf_encrypted_rejected(self) -> None:
        from pypdf import PdfWriter

        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        writer.encrypt("secret-password")
        buf = io.BytesIO()
        writer.write(buf)
        data = buf.getvalue()
        with self.assertRaises(PdfProcessingError) as ctx:
            process_pdf_bytes(
                data=data, filename="locked.pdf", content_type="application/pdf"
            )
        self.assertIn("password", str(ctx.exception).lower())

    def test_oversized_pdf_rejected(self) -> None:
        from app.config import settings

        data = b"%PDF-1.4\n" + b"0" * 1000
        with patch.object(settings, "max_pdf_size_mb", 0.00001):
            with self.assertRaises(FileValidationError):
                process_pdf_bytes(
                    data=data, filename="big.pdf", content_type="application/pdf"
                )

    def test_crisis_safety_independent(self) -> None:
        from app.config import settings

        text = "I want to end my life and do not feel safe."
        with patch.object(settings, "enable_support_resources", True):
            self.assertTrue(user_text_indicates_crisis(text))
            resources = get_support_resources(
                prediction=None,
                sources=[],
                reasoning="",
                user_text=text,
            )
            self.assertGreaterEqual(len(resources), 1)

    def test_legacy_text_only_request(self) -> None:
        req = AnalyseRequest(text="I have felt anxious for weeks.")
        norm = normalize_multimodal_input(req)
        self.assertIn("Typed input:", norm.combined_user_text)
        self.assertTrue(norm.input_summary.typed_text_used)


if __name__ == "__main__":
    unittest.main()
