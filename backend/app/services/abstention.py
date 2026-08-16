"""Trust-aware abstention for TrustMind analyse responses."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings


ABSTENTION_MESSAGE = (
    "TrustMind abstained because confidence was below the trust threshold — "
    "this is intentional, not a broken result. Add more detail and try again."
)
ABSTENTION_RECOMMENDATION = (
    "Consider contacting your GP, NHS services or your university wellbeing team "
    "if you require support."
)

# Aligns with frontend hard guardrail / input-ambiguity heuristic (~12 words).
SHORT_INPUT_WORD_LIMIT = 12
_SHORT_INPUT_WORD_LIMIT = SHORT_INPUT_WORD_LIMIT  # backward-compatible alias

SHORT_INPUT_CLIENT_MESSAGE = (
    "Please write at least 2–4 sentences (about 12+ words). "
    "A single word or short phrase is not enough for a reliable assessment."
)

ABSTENTION_MESSAGE_SHORT_INPUT = (
    "This is intentional — not a broken result. Your check-in was too short for a "
    "confident assessment, so TrustMind abstained rather than guessing. "
    "Please write at least 2–4 sentences (about 12+ words) and try again."
)
ABSTENTION_RECOMMENDATION_SHORT_INPUT = (
    "Example: \"I've been feeling stressed for about two weeks. It's hard to sleep "
    "and I'm falling behind on coursework. Things feel heavier than usual.\" "
    + ABSTENTION_RECOMMENDATION
)


@dataclass
class AbstentionDecision:
    """Outcome of the confidence-threshold check."""

    abstained: bool
    status: str  # "accepted" | "abstained"
    message: str
    recommendation: str


def _word_count(text: str | None) -> int:
    if not text or not str(text).strip():
        return 0
    return len(str(text).strip().split())


def is_underspecified_input(
    *,
    typed_text: str | None = None,
    speech_transcript: str | None = None,
    file_text: str | None = None,
    combined_text: str | None = None,
) -> bool:
    """
    True when user content has too few words for a reliable assessment.

    Prefer raw modality fields over labelled ``combined_text`` (which includes
    prefixes like "Typed input:").
    """
    typed_n = _word_count(typed_text)
    speech_n = _word_count(speech_transcript)
    file_n = _word_count(file_text)
    modality_total = typed_n + speech_n + file_n
    if modality_total > 0:
        return modality_total < SHORT_INPUT_WORD_LIMIT
    combined_n = _word_count(combined_text)
    return 0 < combined_n < SHORT_INPUT_WORD_LIMIT


def should_abstain(confidence: float) -> bool:
    """Return True when confidence is below the configured threshold."""
    if not settings.enable_abstention:
        return False
    try:
        value = float(confidence)
    except (TypeError, ValueError):
        return True
    return value < float(settings.confidence_threshold)


def apply_abstention(
    confidence: float,
    *,
    text: str | None = None,
    typed_text: str | None = None,
    speech_transcript: str | None = None,
    file_text: str | None = None,
) -> AbstentionDecision:
    """
    Decide whether to withhold a prediction.

    Does not fabricate labels — callers must null out prediction when abstained.
    Optional text fields only adjust user-facing copy for very short inputs.
    """
    if should_abstain(confidence):
        short = is_underspecified_input(
            typed_text=typed_text,
            speech_transcript=speech_transcript,
            file_text=file_text,
            combined_text=text,
        )
        return AbstentionDecision(
            abstained=True,
            status="abstained",
            message=(
                ABSTENTION_MESSAGE_SHORT_INPUT if short else ABSTENTION_MESSAGE
            ),
            recommendation=(
                ABSTENTION_RECOMMENDATION_SHORT_INPUT
                if short
                else ABSTENTION_RECOMMENDATION
            ),
        )
    return AbstentionDecision(
        abstained=False,
        status="accepted",
        message="",
        recommendation="",
    )
