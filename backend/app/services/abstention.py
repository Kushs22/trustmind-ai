"""Trust-aware abstention for TrustMind analyse responses."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings


ABSTENTION_MESSAGE = (
    "The system did not have enough reliable evidence to provide a confident assessment."
)
ABSTENTION_RECOMMENDATION = (
    "Consider contacting your GP, NHS services or your university wellbeing team "
    "if you require support."
)

# Aligns with frontend soft guardrail / input-ambiguity heuristic (~12 words).
_SHORT_INPUT_WORD_LIMIT = 12

ABSTENTION_MESSAGE_SHORT_INPUT = (
    "Your check-in was quite short, so TrustMind abstained rather than guessing. "
    "This is intentional when confidence is below the trust threshold."
)
ABSTENTION_RECOMMENDATION_SHORT_INPUT = (
    "Add 2–4 sentences about how long this has lasted and how it affects sleep, "
    "study, or daily life, then try again. " + ABSTENTION_RECOMMENDATION
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
) -> AbstentionDecision:
    """
    Decide whether to withhold a prediction.

    Does not fabricate labels — callers must null out prediction when abstained.
    Optional ``text`` only adjusts user-facing copy for very short inputs.
    """
    if should_abstain(confidence):
        short = 0 < _word_count(text) < _SHORT_INPUT_WORD_LIMIT
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
