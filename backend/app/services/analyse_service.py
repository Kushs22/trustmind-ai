from dataclasses import dataclass, field
import logging
import re

from app.schemas.analyse import AnalyseRequest

logger = logging.getLogger(__name__)


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
    early_signs: list[str] = field(default_factory=list)
    # Extended fields
    status: str = "accepted"
    prediction: str | None = None
    confidence: float = 0.0
    reasoning: str = ""
    sources: list[str] = field(default_factory=list)
    message: str = ""
    recommendation: str = ""
    pipeline_used: str = "LLM"
    support_resources: list[dict[str, str]] = field(default_factory=list)
    disclaimer: str = ""
    privacy_notice: str = ""
    human_oversight: str = ""


# Heuristic theme detectors for keyword fallback (non-LLM mode)
THEME_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("self-harm / suicidal crisis signs", (
        "suicide", "suicidal", "kill myself", "end my life", "want to die",
        "self harm", "self-harm", "hurt myself", "ending it",
    )),
    ("anxiety / worry", (
        "anxious", "anxiety", "worried", "worry", "nervous", "on edge", "uneasy",
    )),
    ("panic-like symptoms", (
        "panic", "panic attack", "can't breathe", "cant breathe", "heart racing",
    )),
    ("low mood / depressive signs", (
        "depressed", "depression", "hopeless", "worthless", "empty", "numb",
        "no point", "don't care anymore", "dont care anymore", "sad all the time",
    )),
    ("stress / burnout", (
        "burnout", "burnt out", "burned out", "overwhelmed", "stressed", "stress",
        "pressure", "exhausted",
    )),
    ("sleep disruption", (
        "insomnia", "can't sleep", "cant sleep", "nightmares", "tired all the time",
        "no sleep",
    )),
    ("loneliness / social withdrawal", (
        "lonely", "alone", "isolated", "no friends", "withdraw", "nobody cares",
    )),
    ("mood fluctuation signs", (
        "mood swings", "up and down", "manic", "high then low", "bipolar",
    )),
    ("trauma-related stress signs", (
        "flashback", "trauma", "triggered", "ptsd", "nightmare about",
    )),
    ("obsessive / repetitive worry signs", (
        "can't stop thinking", "cant stop thinking", "obsess", "compulsion",
        "checking over and over", "ocd",
    )),
    ("eating / body image concerns", (
        "binge", "purge", "hate my body", "starving", "anorex", "bulim",
        "don't eat", "dont eat",
    )),
    ("substance / coping concerns", (
        "drinking too much", "getting drunk", "high all the time", "weed to cope",
        "pills to cope", "alcohol to cope",
    )),
    ("irritability / anger", (
        "angry", "furious", "rage", "irritable", "snapping at",
    )),
    ("concentration / cognitive fog", (
        "can't focus", "cant focus", "brain fog", "can't concentrate",
        "cant concentrate", "memory is bad",
    )),
    ("grief / loss", (
        "grief", "grieving", "passed away", "lost my", "funeral", "bereav",
    )),
    ("attention / restlessness signs", (
        "can't sit still", "cant sit still", "restless", "adhd", "distracted",
    )),
    ("relationship / interpersonal distress", (
        "breakup", "broke up", "toxic relationship", "argument with", "fight with",
    )),
    ("academic / work pressure", (
        "exam", "deadline", "dissertation", "assignment", "failing", "workload",
        "coursework",
    )),
]

SAFETY_NOTE = (
    "This tool provides wellbeing support information and should not be considered "
    "a medical diagnosis. This tool should not replace qualified healthcare professionals."
)

DEFAULT_NEXT_STEPS = [
    "Consider speaking to someone you trust",
    "Explore UWE wellbeing support",
    "Contact professional support if feelings worsen",
]


def _detect_early_signs(text: str) -> list[str]:
    lowered = text.lower()
    found: list[str] = []
    for theme, patterns in THEME_PATTERNS:
        if any(p in lowered for p in patterns):
            found.append(theme)
    return found


def _run_keyword_analysis(request: AnalyseRequest) -> AnalyseResult:
    """Fallback rule-based early-sign detection when LLM is unavailable."""
    text = request.text
    early_signs = _detect_early_signs(text)
    crisis = any("suicidal" in s or "self-harm" in s for s in early_signs)

    if crisis:
        from app.services.support_resources import get_support_resources

        return AnalyseResult(
            concern_level="High",
            ai_confidence="62%",
            uncertainty_level="Medium",
            grounding_status="Crisis support resources recommended",
            abstention_status="Abstention triggered — no clinical prediction",
            explanation=(
                "Possible early signs related to self-harm or crisis language were detected. "
                "TrustMind AI does not diagnose or provide crisis counselling. "
                "Please consider urgent support options."
            ),
            safe_next_steps=[
                "Contact emergency services if you are in immediate danger",
                "Reach out to Samaritans (116 123) or local crisis support",
                "Speak to a trusted person or UWE wellbeing support",
            ],
            safety_note=SAFETY_NOTE,
            early_signs=early_signs or ["self-harm / suicidal crisis signs"],
            status="abstained",
            prediction=None,
            confidence=0.62,
            reasoning="Crisis language detected — prediction withheld.",
            sources=[],
            message="The model is not sufficiently confident to provide a reliable wellbeing assessment.",
            recommendation=(
                "Consider contacting your GP, NHS services or your university wellbeing team "
                "if you require support."
            ),
            pipeline_used="keyword_fallback",
            support_resources=get_support_resources(force=True),
            disclaimer=SAFETY_NOTE,
            privacy_notice=(
                "No unnecessary storage of personal text. Raw check-in text is only saved when "
                "you explicitly opt in and disable private mode."
            ),
            human_oversight="This tool should not replace qualified healthcare professionals.",
        )

    n = len(early_signs)
    if n >= 3:
        concern, confidence, uncertainty = "Moderate", "74%", "Medium"
        explanation = (
            "Several possible early wellbeing signs were detected in your message "
            f"(for example: {', '.join(early_signs[:3])}). "
            "This is not a diagnosis, but supportive resources may help."
        )
        conf_f = 0.74
    elif n >= 1:
        concern, confidence, uncertainty = "Low", "78%", "Medium"
        explanation = (
            "Some possible early wellbeing signs were detected "
            f"({', '.join(early_signs)}). "
            "This is not a diagnosis. Gentle support and self-check-ins can still be useful."
        )
        conf_f = 0.78
    else:
        concern, confidence, uncertainty = "Low", "85%", "Low"
        early_signs = []
        explanation = (
            "No strong early distress signs were detected in this message. "
            "This is not a diagnosis. You can check in again if how you feel changes."
        )
        conf_f = 0.85

    return AnalyseResult(
        concern_level=concern,
        ai_confidence=confidence,
        uncertainty_level=uncertainty,
        grounding_status="Early-sign wellbeing assessment (keyword fallback)",
        abstention_status="Prediction accepted",
        explanation=explanation,
        safe_next_steps=DEFAULT_NEXT_STEPS.copy(),
        safety_note=SAFETY_NOTE,
        early_signs=early_signs,
        status="accepted",
        prediction=None,
        confidence=conf_f,
        reasoning=explanation,
        sources=[],
        pipeline_used="keyword_fallback",
        disclaimer=SAFETY_NOTE,
        privacy_notice=(
            "No unnecessary storage of personal text. Raw check-in text is only saved when "
            "you explicitly opt in and disable private mode."
        ),
        human_oversight="This tool should not replace qualified healthcare professionals.",
    )


def run_analysis(request: AnalyseRequest) -> AnalyseResult:
    """
    Run the configured analyse pipeline (LLM or LLM+RAG).

    Frontend never talks to the LLM directly — this is the sole entry point.
    """
    request = AnalyseRequest(
        text=re.sub(r"\s+", " ", request.text).strip(),
        save_to_history=request.save_to_history,
        analyse_privately=request.analyse_privately,
    )

    from app.config import settings
    from app.services.pipeline_controller import run_configured_pipeline

    backend = settings.analyse_backend.lower().strip()
    if backend == "keywords":
        return _run_keyword_analysis(request)

    # auto / llm → dissertation LLM or RAG pipelines via controller
    try:
        pipe = run_configured_pipeline(request)
        return AnalyseResult(
            concern_level=pipe.concern_level,
            ai_confidence=pipe.ai_confidence,
            uncertainty_level=pipe.uncertainty_level,
            grounding_status=pipe.grounding_status,
            abstention_status=pipe.abstention_status,
            explanation=pipe.explanation,
            safe_next_steps=pipe.safe_next_steps,
            safety_note=pipe.safety_note,
            early_signs=pipe.early_signs,
            status=pipe.status,
            prediction=pipe.prediction,
            confidence=pipe.confidence,
            reasoning=pipe.reasoning,
            sources=pipe.sources,
            message=pipe.message,
            recommendation=pipe.recommendation,
            pipeline_used=pipe.pipeline_used,
            support_resources=pipe.support_resources,
            disclaimer=pipe.disclaimer,
            privacy_notice=pipe.privacy_notice,
            human_oversight=pipe.human_oversight,
        )
    except Exception:
        logger.exception("Configured pipeline failed; using keyword fallback")
        return _run_keyword_analysis(request)
