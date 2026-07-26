from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.multimodal import (
    AttachmentContext,
    InputSummaryOut,
    ProcessedAttachmentOut,
)


class AnalyseRequest(BaseModel):
    """
    Wellbeing analyse request.

    Prefer multimodal fields (`typed_text`, `speech_transcript`, attachment contexts).
    Legacy clients may send `text` alone.
    """

    text: str = Field(
        default="",
        max_length=12000,
        description="Legacy free-text field (used when typed_text is empty).",
    )
    typed_text: str = Field(default="", max_length=12000)
    speech_transcript: str = Field(default="", max_length=12000)
    image_context: list[AttachmentContext] = Field(default_factory=list)
    pdf_context: list[AttachmentContext] = Field(default_factory=list)
    save_to_history: bool = False
    analyse_privately: bool = True
    # Per-request pipeline choice for the dissertation demo (overrides USE_RAG when set).
    # auto = honour server USE_RAG; llm = standalone GPT; rag = hybrid BM25+FAISS + GPT
    pipeline_mode: Literal["auto", "llm", "rag"] = "auto"
    include_debug: bool = False

    @model_validator(mode="after")
    def require_some_content(self) -> "AnalyseRequest":
        has_text = bool((self.text or "").strip() or (self.typed_text or "").strip())
        has_speech = bool((self.speech_transcript or "").strip())
        has_img = any(
            i.included and ((i.extracted_text or "").strip() or (i.summary or "").strip())
            for i in (self.image_context or [])
        )
        has_pdf = any(
            p.included and ((p.extracted_text or "").strip() or (p.summary or "").strip())
            for p in (self.pdf_context or [])
        )
        if not (has_text or has_speech or has_img or has_pdf):
            raise ValueError(
                "Provide typed text, a speech transcript, or included image/PDF context."
            )
        if len(self.image_context or []) > 5:
            raise ValueError("Too many image context items.")
        if len(self.pdf_context or []) > 3:
            raise ValueError("Too many PDF context items.")
        return self


class SupportResourceOut(BaseModel):
    name: str
    description: str
    contact: str
    url: str


class ConfidenceBreakdownOut(BaseModel):
    """Calibrated confidence components on a 0–100 scale (null = not applicable)."""

    retrieval_similarity: int | None = None
    source_agreement: int | None = None
    llm_confidence: int = 0
    classification_consistency: int | None = None
    retrieval_coverage: int | None = None
    input_clarity: int | None = None


class TrustSignalsOut(BaseModel):
    model_confidence: int = 0
    evidence_strength: int | None = None
    retrieval_quality: int | None = None


class GroundingOut(BaseModel):
    status: str = "not_applicable"
    label: str = "Standalone model response"


class EvidenceItemOut(BaseModel):
    source_id: str = ""
    organisation: str = ""
    title: str = ""
    topic: str = ""
    url: str = ""
    retrieval_score: float = 0.0
    reason_retrieved: str = ""
    display_label: str = ""


class AnalyseDebugOut(BaseModel):
    latency_ms: float = 0.0
    n_retrieved_chunks: int = 0
    openai_model: str = ""
    embedding_model: str = "text-embedding-3-small"
    confidence_threshold: float = 0.75
    grounding_retrieval_quality_min: int = 55
    grounding_evidence_strength_min: int = 50
    pipeline_used: str = ""
    consistency_runs: int = 0


class AnalyseResponse(BaseModel):
    """Unified analyse response for LLM and LLM+RAG modes."""

    id: str | None = None
    # Dissertation / demo fields
    status: str = "accepted"  # accepted | abstained
    prediction: str | None = None
    prediction_display: str | None = None
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
    potential_indicators: list[str] = []
    saved_to_history: bool = False
    # Evidence-based calibration / trust
    confidence_breakdown: ConfidenceBreakdownOut | None = None
    uncertainty: str = ""
    trust_signals: TrustSignalsOut | None = None
    grounding: GroundingOut | None = None
    evidence_used: list[EvidenceItemOut] = []
    sources_detail: list[EvidenceItemOut] = []
    safety_triggered: bool = False
    debug: AnalyseDebugOut | None = None
    # Multimodal metadata (attachments are user context, not trusted RAG)
    input_summary: InputSummaryOut | None = None
    processed_attachments: list[ProcessedAttachmentOut] = []
