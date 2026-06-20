from dataclasses import dataclass

from app.schemas.analyse import AnalyseRequest


@dataclass
class AnalyseResult:
    concern_level: str
    ai_confidence: str
    uncertainty_level: str
    grounding_status: str
    abstention_status: str
    explanation: str
    safe_next_steps: list[str]
    safety_note: str


DISTRESS_KEYWORDS = (
    "sad",
    "lonely",
    "alone",
    "stress",
    "stressed",
    "anxious",
    "anxiety",
    "overwhelmed",
    "hopeless",
    "tired",
    "exhausted",
    "cry",
    "crying",
    "worthless",
    "panic",
)

CRISIS_KEYWORDS = (
    "suicide",
    "kill myself",
    "end my life",
    "self harm",
    "self-harm",
    "hurt myself",
)

SAFETY_NOTE = (
    "This is not a diagnosis or therapy service. "
    "If you feel at immediate risk, contact emergency or crisis support."
)

DEFAULT_NEXT_STEPS = [
    "Consider speaking to someone you trust",
    "Explore UWE wellbeing support",
    "Contact professional support if feelings worsen",
]


def run_analysis(request: AnalyseRequest) -> AnalyseResult:
    """Run wellbeing analysis.

    Replace keyword logic with your ML/NLP pipeline when ready.
    """
    text = request.text.lower()
    distress_hits = sum(1 for word in DISTRESS_KEYWORDS if word in text)
    crisis_hits = sum(1 for phrase in CRISIS_KEYWORDS if phrase in text)

    if crisis_hits > 0:
        return AnalyseResult(
            concern_level="High",
            ai_confidence="62%",
            uncertainty_level="Medium",
            grounding_status="Crisis support resources recommended",
            abstention_status="Abstention triggered — no clinical prediction",
            explanation=(
                "The text includes language that may indicate immediate risk. "
                "TrustMind AI does not provide diagnosis or crisis counselling. "
                "Please consider urgent support options."
            ),
            safe_next_steps=[
                "Contact emergency services if you are in immediate danger",
                "Reach out to Samaritans (116 123) or local crisis support",
                "Speak to a trusted person or UWE wellbeing support",
            ],
            safety_note=SAFETY_NOTE,
        )

    if distress_hits >= 3:
        concern = "Moderate"
        confidence = "74%"
        uncertainty = "Medium"
        explanation = (
            "The text suggests signs of sadness, loneliness, and emotional distress. "
            "This does not indicate a diagnosis, but it may suggest that supportive "
            "resources could be helpful."
        )
    elif distress_hits >= 1:
        concern = "Low"
        confidence = "81%"
        uncertainty = "Low"
        explanation = (
            "The text shows some emotional strain or stress-related language. "
            "This is not a diagnosis, but gentle support may be beneficial."
        )
    else:
        concern = "Low"
        confidence = "88%"
        uncertainty = "Low"
        explanation = (
            "The text does not strongly indicate elevated emotional distress signals. "
            "This is not a diagnosis. Continue monitoring how you feel over time."
        )

    return AnalyseResult(
        concern_level=concern,
        ai_confidence=confidence,
        uncertainty_level=uncertainty,
        grounding_status="Evidence-informed support context available",
        abstention_status="Prediction accepted",
        explanation=explanation,
        safe_next_steps=DEFAULT_NEXT_STEPS.copy(),
        safety_note=SAFETY_NOTE,
    )
