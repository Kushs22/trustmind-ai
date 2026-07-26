"""Schemas for speech transcription."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TranscriptionResponse(BaseModel):
    status: str = "completed"
    transcript: str = ""
    language: str = "en"
    duration_seconds: float | None = None
    warnings: list[str] = Field(default_factory=list)
