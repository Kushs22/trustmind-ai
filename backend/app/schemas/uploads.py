"""Schemas for image and PDF preprocessing responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ImageProcessResponse(BaseModel):
    filename: str
    summary: str = ""
    extracted_text: str = ""
    contains_text: bool = False
    safety_flags: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    useful_context: bool = True


class PdfProcessResponse(BaseModel):
    filename: str
    page_count: int = 0
    extracted_text: str = ""
    document_summary: str = ""
    safety_flags: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    is_scanned: bool = False
