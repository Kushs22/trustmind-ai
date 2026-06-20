from datetime import datetime

from pydantic import BaseModel


class CheckInResponse(BaseModel):
    id: str
    date: str
    concern: str
    confidence: str
    abstained: bool
    preview: str | None
    is_private: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardStatsResponse(BaseModel):
    saved_analyses: int
    avg_ai_confidence: int | None
    abstention_count: int
    privacy_mode: str
