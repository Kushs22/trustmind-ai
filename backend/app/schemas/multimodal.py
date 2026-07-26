"""Schemas for multimodal analyse input normalisation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AttachmentContext(BaseModel):
    """User-confirmed extracted context from an attachment (not trusted RAG)."""

    filename: str = ""
    extracted_text: str = ""
    summary: str = ""
    included: bool = True
    warnings: list[str] = Field(default_factory=list)


class InputSourceItem(BaseModel):
    type: Literal["typed_text", "speech_transcript", "image", "pdf"]
    included: bool = True
    filename: str | None = None


class InputSummaryOut(BaseModel):
    typed_text_used: bool = False
    speech_transcript_used: bool = False
    image_count: int = 0
    pdf_count: int = 0


class ProcessedAttachmentOut(BaseModel):
    type: Literal["image", "pdf", "audio"]
    filename: str = ""
    status: str = "processed"
    included_in_analysis: bool = True
    warnings: list[str] = Field(default_factory=list)


class NormalisedMultimodalInput(BaseModel):
    combined_user_text: str
    typed_text: str = ""
    speech_transcript: str = ""
    input_sources: list[InputSourceItem] = Field(default_factory=list)
    input_summary: InputSummaryOut = Field(default_factory=InputSummaryOut)
    processed_attachments: list[ProcessedAttachmentOut] = Field(default_factory=list)
    user_context: dict[str, Any] = Field(default_factory=dict)
