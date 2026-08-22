from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CheckInResponse(BaseModel):
    id: str
    date: str
    concern: str
    confidence: str
    abstained: bool
    preview: str | None
    is_private: bool
    created_at: datetime
    support_urgency: int | None = None
    support_urgency_band: Literal["low", "moderate", "elevated", "urgent"] | None = None
    support_urgency_uncertain: bool = False

    model_config = {"from_attributes": True}


class CheckInDetailResponse(BaseModel):
    """Full saved check-in for dashboard detail / resume."""

    id: str
    date: str
    concern: str
    confidence: str
    uncertainty_level: str
    grounding_status: str
    abstention_status: str
    abstained: bool
    explanation: str
    safe_next_steps: list[str]
    safety_note: str
    preview: str | None
    is_private: bool
    created_at: datetime
    support_urgency: int | None = Field(default=None, ge=0, le=100)
    support_urgency_band: Literal["low", "moderate", "elevated", "urgent"] | None = None
    support_urgency_rationale: str | None = None
    support_urgency_uncertain: bool = False


class DashboardStatsResponse(BaseModel):
    saved_analyses: int
    avg_ai_confidence: int | None
    abstention_count: int
    privacy_mode: str
