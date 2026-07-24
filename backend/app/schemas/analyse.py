from typing import Literal

from pydantic import BaseModel, Field


class AnalyseRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=12000,
        description="Free-text wellbeing check-in (not stored unless you opt in).",
    )
    save_to_history: bool = False
    analyse_privately: bool = True
    # Per-request pipeline choice for the dissertation demo (overrides USE_RAG when set).
    # auto = honour server USE_RAG; llm = standalone GPT; rag = hybrid BM25+FAISS + GPT
    pipeline_mode: Literal["auto", "llm", "rag"] = "auto"


class SupportResourceOut(BaseModel):
    name: str
    description: str
    contact: str
    url: str


class AnalyseResponse(BaseModel):
    """Unified analyse response for LLM and LLM+RAG modes."""

    id: str | None = None
    # Dissertation / demo fields
    status: str = "accepted"  # accepted | abstained
    prediction: str | None = None
    confidence: float = 0.0
    reasoning: str = ""
    sources: list[str] = []
    message: str = ""
    recommendation: str = ""
    pipeline_used: str = "LLM"
    support_resources: list[SupportResourceOut] = []
    disclaimer: str = ""
    privacy_notice: str = ""
    human_oversight: str = ""
    # Legacy product fields (dashboard / history compatibility)
    concern_level: str
    ai_confidence: str
    uncertainty_level: str
    grounding_status: str
    abstention_status: str
    explanation: str
    safe_next_steps: list[str]
    safety_note: str
    early_signs: list[str] = []
    saved_to_history: bool = False
