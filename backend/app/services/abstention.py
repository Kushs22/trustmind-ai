"""Trust-aware abstention for TrustMind analyse responses."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings


ABSTENTION_MESSAGE = (
    "We're holding back a labelled category for now because we aren't confident "
    "enough yet — that is intentional care, not a broken result. Crisis support "
    "is still available if you need it."
)
ABSTENTION_RECOMMENDATION = (
    "If you'd like support, consider contacting your GP, NHS services, or your "
    "university wellbeing team."
)

# Short check-ins skip abstention. Longer inputs keep a trust floor, but only
# withhold when uncertainty is Very High (< ~45%) or there is no label to show.
SHORT_INPUT_WORD_LIMIT = 12
_SHORT_INPUT_WORD_LIMIT = SHORT_INPUT_WORD_LIMIT  # backward-compatible alias
# Aligns with uncertainty_from_confidence "Very High" (< 0.45).
LONG_INPUT_MIN_CONFIDENCE = 0.45

# Soft tip only (never used as a hard 422 rejection).
SHORT_INPUT_CLIENT_MESSAGE = (
    "Tip: the more you share, the better we can support you — how long this has "
    "lasted, sleep, study, or daily life often helps. One-word check-ins still work."
)

# When short inputs somehow still abstain (e.g. missing prediction), keep copy clear.
ABSTENTION_MESSAGE_SHORT_INPUT = (
    "We're holding back a labelled category for now rather than guessing — that is "
    "intentional. Try adding a sentence or two about how long this has lasted and "
    "how it affects you."
)
ABSTENTION_RECOMMENDATION_SHORT_INPUT = (
    "Example: \"I've been feeling stressed for about two weeks. It's hard to sleep "
    "and I'm falling behind on coursework. Things feel heavier than usual.\" "
    + ABSTENTION_RECOMMENDATION
)

LIMITED_CONTEXT_DISCLAIMER = (
    "You've shared only a little so far, so this read is gentle and provisional — "
    "not a diagnosis. The more you share, the better we can support you."
)
LIMITED_CONFIDENCE_DISCLAIMER = (
    "We're showing a category from what you wrote, with more limited confidence "
    "than a fully certain read — this is not a diagnosis."
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
    limited_confidence: bool = False


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


def _has_usable_prediction(prediction: str | None) -> bool:
    return bool(prediction and str(prediction).strip())


def apply_abstention(
    confidence: float,
    *,
    text: str | None = None,
    typed_text: str | None = None,
    speech_transcript: str | None = None,
    file_text: str | None = None,
    prediction: str | None = None,
) -> AbstentionDecision:
    """
    Decide whether to withhold a prediction.

    Very short inputs skip abstention so one-word check-ins still return a label;
    callers should attach a limited-context disclaimer.

    Longer inputs still use the trust layer, but a detailed check-in with a
    model label is shown unless confidence is in the Very High uncertainty
    band (below LONG_INPUT_MIN_CONFIDENCE). Mid-band scores keep the label
    and flag limited confidence instead of withholding entirely.
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

    if not settings.enable_abstention:
        return AbstentionDecision(
            abstained=False,
            status="accepted",
            message="",
            recommendation="",
        )

    has_label = _has_usable_prediction(prediction)
    truly_unsure = (not has_label) or should_abstain(
        confidence, threshold=LONG_INPUT_MIN_CONFIDENCE
    )
    if truly_unsure:
        return AbstentionDecision(
            abstained=True,
            status="abstained",
            message=ABSTENTION_MESSAGE,
            recommendation=ABSTENTION_RECOMMENDATION,
        )

    limited = should_abstain(confidence)
    return AbstentionDecision(
        abstained=False,
        status="accepted",
        message=LIMITED_CONFIDENCE_DISCLAIMER if limited else "",
        recommendation="",
        limited_confidence=limited,
    )
