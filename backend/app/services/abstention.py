"""Trust-aware abstention for TrustMind analyse responses."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings


ABSTENTION_MESSAGE = (
    "The model is not sufficiently confident to provide a reliable wellbeing assessment."
)
ABSTENTION_RECOMMENDATION = (
    "Consider contacting your GP, NHS services or your university wellbeing team "
    "if you require support."
)


@dataclass
class AbstentionDecision:
    """Outcome of the confidence-threshold check."""

    abstained: bool
    status: str  # "accepted" | "abstained"
    message: str
    recommendation: str


def should_abstain(confidence: float) -> bool:
    """Return True when confidence is below the configured threshold."""
    if not settings.enable_abstention:
        return False
    try:
        value = float(confidence)
    except (TypeError, ValueError):
        return True
    return value < float(settings.confidence_threshold)


def apply_abstention(confidence: float) -> AbstentionDecision:
    """
    Decide whether to withhold a prediction.

    Does not fabricate labels — callers must null out prediction when abstained.
    """
    if should_abstain(confidence):
        return AbstentionDecision(
            abstained=True,
            status="abstained",
            message=ABSTENTION_MESSAGE,
            recommendation=ABSTENTION_RECOMMENDATION,
        )
    return AbstentionDecision(
        abstained=False,
        status="accepted",
        message="",
        recommendation="",
    )
