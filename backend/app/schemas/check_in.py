from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.analyse import SupportResourceOut


class ChatMessageOut(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: str | None = None
    safety_triggered: bool = False


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
    """Full saved check-in for dashboard detail / resume chat."""

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
    messages: list[ChatMessageOut] = Field(default_factory=list)


class ChatFollowUpRequest(BaseModel):
    """Append a user message to a saved check-in thread (or ephemeral client thread)."""

    message: str = Field(..., min_length=1, max_length=4000)
    check_in_id: str | None = Field(default=None, max_length=36)
    history: list[ChatMessageOut] = Field(default_factory=list)


class ChatFollowUpResponse(BaseModel):
    check_in_id: str | None = None
    reply: str
    safety_triggered: bool = False
    support_resources: list[SupportResourceOut] = Field(default_factory=list)
    messages: list[ChatMessageOut] = Field(default_factory=list)
    persisted: bool = False


class DashboardStatsResponse(BaseModel):
    saved_analyses: int
    avg_ai_confidence: int | None
    abstention_count: int
    privacy_mode: str
