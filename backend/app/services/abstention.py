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

# Short check-ins are allowed; longer inputs keep the global trust threshold.
SHORT_INPUT_WORD_LIMIT = 12
_SHORT_INPUT_WORD_LIMIT = SHORT_INPUT_WORD_LIMIT  # backward-compatible alias

# Soft tip only (never used as a hard 422 rejection).
SHORT_INPUT_CLIENT_MESSAGE = (
    "Tip: a little more detail (how long this has lasted, sleep, study, daily life) "
    "usually improves assessment quality — short check-ins are still analysed."
)

# When short inputs somehow still abstain (e.g. missing prediction), keep copy clear.
ABSTENTION_MESSAGE_SHORT_INPUT = (
    "This is intentional — not a broken result. Confidence stayed too low even for a "
    "short check-in, so TrustMind withheld a category label rather than guessing. "
    "Try adding a sentence or two about how long this has lasted and how it affects you."
)
ABSTENTION_RECOMMENDATION_SHORT_INPUT = (
    "Example: \"I've been feeling stressed for about two weeks. It's hard to sleep "
    "and I'm falling behind on coursework. Things feel heavier than usual.\" "
    + ABSTENTION_RECOMMENDATION
)

LIMITED_CONTEXT_DISCLAIMER = (
    "Limited context / low confidence: this check-in was very short, so the "
    "assessment is provisional and not a diagnosis. Adding a little more detail "
    "usually improves reliability."
)

# Clear single-word / short-phrase wellbeing cues → research labels (SWMH schema).
SHORT_WELLBEING_LABELS: dict[str, str] = {
    "stressed": "Anxiety",
    "stress": "Anxiety",
    "anxious": "Anxiety",
    "anxiety": "Anxiety",
    "worried": "Anxiety",
    "worry": "Anxiety",
    "nervous": "Anxiety",
    "panic": "Anxiety",
    "overwhelmed": "Anxiety",
    "sad": "depression",
    "depressed": "depression",
    "depression": "depression",
    "hopeless": "depression",
    "empty": "depression",
    "numb": "depression",
    "lonely": "offmychest",
    "burnout": "offmychest",
    "exhausted": "offmychest",
    "tired": "offmychest",
    "ok": "offmychest",
    "fine": "offmychest",
    "meh": "offmychest",
}


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
    True when user content has fewer than SHORT_INPUT_WORD_LIMIT words.

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


def short_wellbeing_heuristic_label(text: str | None) -> str | None:
    """Map a clear short wellbeing phrase to a research label, else None."""
    if not text or not str(text).strip():
        return None
    tokens = [t.strip(".,!?;:\"'()[]").lower() for t in str(text).strip().split()]
    tokens = [t for t in tokens if t]
    if not tokens or len(tokens) >= SHORT_INPUT_WORD_LIMIT:
        return None
    # Prefer whole-phrase then individual tokens (last cue wins for "feeling stressed").
    joined = " ".join(tokens)
    if joined in SHORT_WELLBEING_LABELS:
        return SHORT_WELLBEING_LABELS[joined]
    label: str | None = None
    for tok in tokens:
        if tok in SHORT_WELLBEING_LABELS:
            label = SHORT_WELLBEING_LABELS[tok]
    return label


def should_abstain(confidence: float, *, threshold: float | None = None) -> bool:
    """Return True when confidence is below the configured (or override) threshold."""
    if not settings.enable_abstention:
        return False
    try:
        value = float(confidence)
    except (TypeError, ValueError):
        return True
    cut = float(settings.confidence_threshold if threshold is None else threshold)
    return value < cut


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

    Long inputs keep the global confidence threshold (default 0.75).
    Very short inputs skip abstention so one-word check-ins still return a label;
    callers should attach a limited-context disclaimer.
    """
    short = is_underspecified_input(
        typed_text=typed_text,
        speech_transcript=speech_transcript,
        file_text=file_text,
        combined_text=text,
    )
    if short:
        # Prefer usable short-check-in results over forced abstention.
        return AbstentionDecision(
            abstained=False,
            status="accepted",
            message="",
            recommendation="",
        )

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
