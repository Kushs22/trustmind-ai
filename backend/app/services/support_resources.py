"""Configurable support resources for high-risk analyse outcomes."""

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


def is_high_risk_prediction(prediction: str | None) -> bool:
    """True when the predicted class indicates crisis-related content."""
    if not prediction:
        return False
    return prediction.strip().lower() in {"suicidewatch", "self.suicidewatch"}


def sources_indicate_crisis(sources: list[str] | None, reasoning: str = "") -> bool:
    """Heuristic check over retrieved source IDs / reasoning text."""
    blob = " ".join(sources or []).lower() + " " + (reasoning or "").lower()
    return any(hint in blob for hint in CRISIS_SOURCE_HINTS)


def get_support_resources(
    *,
    prediction: str | None = None,
    sources: list[str] | None = None,
    reasoning: str = "",
    force: bool = False,
) -> list[dict[str, str]]:
    """
    Return support resources when enabled and high-risk signals are present.

    Resources are support services only — never framed as a diagnosis.
    """
    if not settings.enable_support_resources and not force:
        return []

    if force or is_high_risk_prediction(prediction) or sources_indicate_crisis(sources, reasoning):
        return [r.to_dict() for r in DEFAULT_RESOURCES]
    return []
