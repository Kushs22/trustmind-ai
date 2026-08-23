"""Classify analyse inputs: first-person check-in vs coaching/instruction wrapper."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Role / coach / system-style instructions (not a lived check-in by themselves).
_COACHING_PATTERNS = (
    r"\bact as\b",
    r"\byou are (?:a |an |my )?(?:compassionate|supportive|helpful)?\s*"
    r"(?:life )?coach\b",
    r"\blife coach\b",
    r"\bconversational partner\b",
    r"\bask me (?:thoughtful )?questions\b",
    r"\bone at a time\b",
    r"\bstart by talking to me\b",
    r"\bguide me toward\b",
    r"\bhelp me explore\b",
    r"\byour (?:role|job|task) is\b",
    r"\bsystem prompt\b",
    r"\binstead of overwhelming me\b",
    r"\blet my answers guide\b",
)

# First-person emotional / experiential signals.
_EMOTION_CUES = (
    "lonely",
    "loneliness",
    "alone",
    "isolated",
    "heartbroken",
    "heartbreak",
    "sad",
    "empty",
    "numb",
    "anxious",
    "anxiety",
    "worried",
    "worry",
    "stress",
    "stressed",
    "overwhelmed",
    "hopeless",
    "exhausted",
    "exhaustion",
    "tired",
    "drained",
    "fatigue",
    "burnout",
    "burnt out",
    "burned out",
    "exam",
    "exams",
    "revision",
    "coursework",
    "dissertation",
    "stuck",
    "guilt",
    "shame",
    "angry",
    "anger",
    "rejected",
    "abandon",
    "grief",
    "miss ",
    "i feel",
    "i've been",
    "ive been",
    "i am feeling",
    "im feeling",
    "i've felt",
    "cant sleep",
    "can't sleep",
    "haven't been sleeping",
    "havent been sleeping",
    "low mood",
    "mood swing",
    "crying",
    "panic",
)

_FIRST_PERSON = re.compile(
    r"\b(i|i'm|im|i've|ive|me|my|myself)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class InputKind:
    """How to treat the user text in the analyse pipeline."""

    is_coaching_request: bool
    has_personal_story: bool
    word_count: int
    emotion_cue_count: int

    @property
    def coaching_without_story(self) -> bool:
        return self.is_coaching_request and not self.has_personal_story

    @property
    def rich_first_person(self) -> bool:
        """First-person emotional narrative suitable for a safe theme label."""
        # Prefer labelling over hard abstain once the check-in is past one-liners
        # and clearly names stress / mood / loneliness (common student demos).
        return (
            self.has_personal_story
            and self.word_count >= 12
            and self.emotion_cue_count >= 1
        )


def _word_count(text: str) -> int:
    return len((text or "").strip().split())


def classify_input_kind(text: str | None) -> InputKind:
    """Detect coaching wrappers vs first-person emotional check-ins."""
    raw = (text or "").strip()
    lower = raw.lower()
    words = _word_count(raw)

    coach_hits = sum(1 for p in _COACHING_PATTERNS if re.search(p, lower))
    is_coaching = coach_hits >= 2 or (
        coach_hits >= 1
        and any(
            p in lower
            for p in (
                "ask me",
                "one at a time",
                "help me explore",
                "act as",
                "life coach",
            )
        )
    )

    emotion_hits = sum(1 for cue in _EMOTION_CUES if cue in lower)
    first_person = bool(_FIRST_PERSON.search(raw))
    # Personal story: first-person + emotion, and not *only* an instruction block.
    # Thin preamble ("I feel lonely…") still counts if ≥2 emotion cues or ≥25 words
    # of non-instruction content after stripping common instruction openers.
    has_story = first_person and emotion_hits >= 1 and (
        emotion_hits >= 2
        or words >= 60
        or (emotion_hits >= 1 and words >= 25 and coach_hits == 0)
    )
    # Pure coaching agendas with a thin feeling clause still count as story if
    # several emotion words appear (user shared how they feel).
    if is_coaching and emotion_hits >= 3 and first_person:
        has_story = True

    return InputKind(
        is_coaching_request=is_coaching,
        has_personal_story=has_story,
        word_count=words,
        emotion_cue_count=emotion_hits,
    )


COACHING_INVITE_REASONING = (
    "It sounds like you want a careful, supportive space to talk something through — "
    "that's completely okay. TrustMind works best when you share what you're going "
    "through in your own words: what happened, how long it's lasted, and how it's "
    "showing up day to day. When you're ready, paste a few sentences about your "
    "situation and I'll reflect with you carefully. This isn't a diagnosis, and "
    "crisis support is still available if you need it."
)

COACHING_WITH_FEELINGS_PREFIX = (
    "I can hear that you're carrying a lot and also hoping for a guided conversation. "
)


def emotion_theme_heuristic(text: str | None) -> str | None:
    """Map rich emotional language to a SWMH theme when the LLM omits a label."""
    t = (text or "").lower()
    if not t.strip():
        return None
    crisis = (
        "kill myself",
        "end my life",
        "want to die",
        "suicidal",
        "don't want to be here",
        "dont want to be here",
        "not wanting to continue",
    )
    if any(c in t for c in crisis):
        return "SuicideWatch"
    anxiety = (
        "anxious",
        "anxiety",
        "panic",
        "worried",
        "worry",
        "dread",
        "on edge",
        "heart racing",
        "can't stop checking",
        "cant stop checking",
        "exam stress",
        "exam",
        "exams",
        "revision",
        "can't focus",
        "cant focus",
        "chest feels tight",
        "overwhelmed",
        "stressed",
        "stress",
    )
    depression = (
        "heartbroken",
        "heartbreak",
        "lonely",
        "loneliness",
        "alone",
        "isolated",
        "empty",
        "numb",
        "hopeless",
        "deeply sad",
        "low mood",
        "can't move forward",
        "cant move forward",
        "emotionally stuck",
        "depressed",
        "worthless",
        "exhausted",
        "exhaustion",
        "drained",
        "burnout",
        "burnt out",
        "burned out",
    )
    bipolar = (
        "mood swing",
        "up and down",
        "barely sleeping then",
        "wired then",
        "high then low",
        "energy swings",
    )
    a = sum(1 for c in anxiety if c in t)
    d = sum(1 for c in depression if c in t)
    b = sum(1 for c in bipolar if c in t)
    if b >= 2 and b >= a and b >= d:
        return "bipolar"
    if a >= d and a >= 2:
        return "Anxiety"
    if d >= 2:
        return "depression"
    if a >= 1:
        return "Anxiety"
    if d >= 1:
        return "depression"
    if any(
        x in t
        for x in ("happy", "relieved", "hopeful", "grateful", "vent", "frustrated")
    ):
        return "offmychest"
    return "offmychest"


def coaching_invite_result_fields() -> dict:
    """Fields for a supportive non-abstention response to pure coaching prompts."""
    return {
        "prediction": "offmychest",
        "confidence": 0.72,
        "reasoning": COACHING_INVITE_REASONING,
        "pipeline_used": "LLM (coaching_invite)",
        "sources": [],
        "retrieved_passages": [],
        "latency_ms": 0.0,
        "error": "",
        "parse_ok": True,
        "confidence_breakdown": {
            "retrieval_similarity": None,
            "source_agreement": None,
            "llm_confidence": 72,
            "classification_consistency": 100,
            "retrieval_coverage": None,
            "input_clarity": 70,
        },
        "uncertainty": "Low",
        "calibration": {"notes": "coaching_invite_path"},
        "consistency_labels": ["offmychest"],
        "llm_confidence_raw": 0.72,
    }
