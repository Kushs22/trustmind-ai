from pydantic import BaseModel, Field


class AnalyseRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    save_to_history: bool = False
    analyse_privately: bool = True


class AnalyseResponse(BaseModel):
    id: str | None = None
    concern_level: str
    ai_confidence: str
    uncertainty_level: str
    grounding_status: str
    abstention_status: str
    explanation: str
    safe_next_steps: list[str]
    safety_note: str
    saved_to_history: bool = False
