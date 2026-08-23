"""Configurable support resources for serious analyse outcomes."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings


@dataclass(frozen=True)
class SupportResource:
    """A non-diagnostic support service entry."""

    name: str
    description: str
    contact: str
    url: str

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "description": self.description,
            "contact": self.contact,
            "url": self.url,
        }


DEFAULT_RESOURCES: tuple[SupportResource, ...] = (
    SupportResource(
        name="NHS Mental Health",
        description="NHS guidance on where to get urgent help for mental health.",
        contact="NHS 111 (option 2) for urgent mental health support in England",
        url="https://www.nhs.uk/nhs-services/mental-health-services/where-to-get-urgent-help-for-mental-health/",
    ),
    SupportResource(
        name="Samaritans",
        description="24/7 listening support if you are struggling to cope.",
        contact="Call 116 123 (UK & ROI)",
        url="https://www.samaritans.org/",
    ),
    SupportResource(
        name="Talk to someone (NHS)",
        description="Find NHS talking therapies and local mental health services.",
        contact="Self-referral available in many areas of England",
        url="https://www.nhs.uk/mental-health/talking-therapies/",
    ),
    SupportResource(
        name="Student Minds",
        description="Student mental health charity with advice and peer support.",
        contact="See website for support options",
        url="https://www.studentminds.org.uk/",
    ),
    SupportResource(
        name="UWE Student Wellbeing",
        description="University of the West of England wellbeing service for students.",
        contact="See UWE wellbeing contact page",
        url="https://www.uwe.ac.uk/life/health-and-wellbeing/get-wellbeing-support/wellbeing-service",
    ),
)

CRISIS_SOURCE_HINTS = (
    "suicid",
    "crisis",
    "samaritan",
    "urgent",
    "self-harm",
    "self harm",
    "116 123",
)

# User-text crisis cues — independent of prediction confidence / RAG
CRISIS_USER_HINTS = (
    "kill myself",
    "end my life",
    "want to die",
    "suicide",
    "suicidal",
    "self harm",
    "self-harm",
    "hurt myself",
    "ending it",
    "better off without me",
    "everyone would be better without me",
    "disappear forever",
)

# Serious wellbeing cues (not necessarily crisis) — still surface support links
SERIOUS_USER_HINTS = (
    "depress",
    "hopeless",
    "lonely",
    "loneliness",
    "worthless",
    "can't go on",
    "cant go on",
    "no point",
    "empty inside",
    "nothing matters",
    "hate myself",
    "self-loathing",
    "panic attack",
    "can't cope",
    "cant cope",
    "breaking down",
    "overwhelmed",
    "want help",
    "need help",
    "struggling",
)

SERIOUS_PREDICTIONS = {
    "depression",
    "anxiety",
    "bipolar",
    "suicidewatch",
    "self.suicidewatch",
    "offmychest",
}


def user_text_indicates_crisis(text: str | None) -> bool:
    """Rule-based safety detector on the raw check-in (independent of model)."""
    blob = (text or "").lower()
    if not blob:
        return False
    return any(hint in blob for hint in CRISIS_USER_HINTS)


def user_text_indicates_serious(text: str | None) -> bool:
    """Depressed / lonely / hopeless-style check-ins that warrant support links."""
    blob = (text or "").lower()
    if not blob:
        return False
    return any(hint in blob for hint in SERIOUS_USER_HINTS)


def is_high_risk_prediction(prediction: str | None) -> bool:
    """True when the predicted class indicates crisis-related content."""
    if not prediction:
        return False
    return prediction.strip().lower() in {"suicidewatch", "self.suicidewatch"}


def is_serious_prediction(prediction: str | None) -> bool:
    """True for SWMH wellbeing classes that should show support contacts."""
    if not prediction:
        return False
    return prediction.strip().lower() in SERIOUS_PREDICTIONS


def sources_indicate_crisis(sources: list[str] | None, reasoning: str = "") -> bool:
    """Heuristic check over retrieved source IDs / reasoning text."""
    blob = " ".join(sources or []).lower()
    return any(hint in blob for hint in CRISIS_SOURCE_HINTS)


def concern_indicates_serious(concern_level: str | None) -> bool:
    """True for Moderate or High concern — show support links."""
    return (concern_level or "").strip().lower() in {"high", "moderate"}


def urgency_indicates_serious(band: str | None) -> bool:
    """True for elevated / urgent support-urgency bands."""
    return (band or "").strip().lower() in {"elevated", "urgent"}


def get_support_resources(
    *,
    prediction: str | None = None,
    sources: list[str] | None = None,
    reasoning: str = "",
    user_text: str = "",
    concern_level: str | None = None,
    support_urgency_band: str | None = None,
    force: bool = False,
) -> list[dict[str, str]]:
    """
    Return support resources when enabled and serious signals are present.

    Triggers on crisis cues, serious wellbeing language (depressed/lonely/hopeless),
    SWMH predictions (depression/anxiety/…), Moderate+ concern, or elevated urgency.
    Safety is independent of classification confidence and RAG success.
    """
    if not settings.enable_support_resources and not force:
        return []

    if (
        force
        or is_high_risk_prediction(prediction)
        or is_serious_prediction(prediction)
        or user_text_indicates_crisis(user_text)
        or user_text_indicates_serious(user_text)
        or sources_indicate_crisis(sources, reasoning)
        or concern_indicates_serious(concern_level)
        or urgency_indicates_serious(support_urgency_band)
    ):
        return [r.to_dict() for r in DEFAULT_RESOURCES]
    return []
