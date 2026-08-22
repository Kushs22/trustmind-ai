"""Trust-aware abstention for TrustMind analyse responses."""

from __future__ import annotations

import re
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

# Soft tip for API clients / input UI only — never inject into result reflection copy
# (the analyse form already shows similar guidance under the input).
LIMITED_CONTEXT_DISCLAIMER = (
    "You've shared only a little so far, so this read is gentle and provisional — "
    "not a diagnosis. The more you share, the better we can support you."
)
# Phrases that must never appear in user-facing result reflections.
SHORT_INPUT_RESULT_LEAK_PHRASES = (
    "you've shared only a little so far",
    "gentle and provisional",
    "the more you share, the better we can support you",
    "this read is gentle and provisional",
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


def short_checkin_reflection(label: str | None, *, user_text: str | None = None) -> str:
    """Warm, useful reflection for short check-ins — never a 'share more' lecture."""
    key = (label or "").strip().lower().replace(" ", "")
    text_l = (user_text or "").lower()
    stressy = any(w in text_l for w in ("stress", "stressed", "overwhelm", "pressure"))

    if key in {"anxiety", "anxiety."} or (stressy and key in {"", "offmychest"}):
        return (
            "It sounds like stress has been weighing on you — that can feel really "
            "heavy. Feeling this way is common when life or study piles up, and you're "
            "not alone in it. If it helps, take a short break, talk with someone you "
            "trust, or look at the support options below. This is a gentle reflection, "
            "not a diagnosis."
        )
    if key == "depression":
        return (
            "It sounds like things have felt heavier lately. Low mood can creep in "
            "quietly, and it makes sense that you'd want to check in. Be kind to "
            "yourself today — a short walk, rest, or talking with someone you trust "
            "can help a little. Support is available if you need it; this isn't a diagnosis."
        )
    if key == "suicidewatch":
        return (
            "I'm really sorry you're feeling this way. You're not alone, and reaching "
            "out matters. Please use the urgent support options below — Samaritans "
            "(116 123) are there to listen any time, and if you're in immediate danger "
            "call 999 or go to A&E."
        )
    if key == "bipolar":
        return (
            "It sounds like your mood or energy has felt up-and-down lately, which can "
            "be unsettling. You're taking a helpful step by checking in. If it helps, "
            "note what's changed recently and talk with someone you trust. This is a "
            "gentle reflection, not a diagnosis."
        )
    return (
        "Thank you for sharing how you're feeling — even a short check-in matters. "
        "Whatever is on your mind, you don't have to carry it alone. If it helps, "
        "take a breath, talk with someone you trust, or explore the support options "
        "below. This is a gentle reflection, not a diagnosis."
    )


def strip_short_input_result_leaks(text: str | None) -> str:
    """Remove input-helper / provisional lecture copy from result reflections."""
    if not text:
        return ""
    out = str(text)
    for phrase in SHORT_INPUT_RESULT_LEAK_PHRASES:
        # Case-insensitive removal of known leak phrases (and the full disclaimer).
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        out = pattern.sub("", out)
    if LIMITED_CONTEXT_DISCLAIMER.lower() in out.lower():
        # Fallback exact-ish wipe if wording drifted slightly.
        out = re.sub(
            r"You've shared only a little so far[^.]*\.",
            "",
            out,
            flags=re.IGNORECASE,
        )
    out = re.sub(r"\s{2,}", " ", out).strip()
    out = re.sub(r"\s+([,.])", r"\1", out)
    return out.strip(" -—")


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
