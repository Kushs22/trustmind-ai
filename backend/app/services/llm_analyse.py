"""
Open-ended early-sign wellbeing assessment via LLM for TrustMind AI.

Detects a broad range of *possible early wellbeing signs* from any free-form
user message. This is NOT diagnosis or clinical labelling.

Dissertation SWMH 5-class classification remains a separate research notebook.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.config import settings
from app.schemas.analyse import AnalyseRequest
from app.services.analyse_service import AnalyseResult, SAFETY_NOTE

logger = logging.getLogger(__name__)

VALID_CONCERN = {"Low", "Moderate", "High"}
VALID_UNCERTAINTY = {"Low", "Medium", "High"}
VALID_ABSTENTION = {
    "Prediction accepted",
    "Abstention triggered — no clinical prediction",
}

# Broad early-sign taxonomy (non-diagnostic theme names shown to users)
EARLY_SIGN_TAXONOMY = [
    "low mood / depressive signs",
    "anxiety / worry",
    "panic-like symptoms",
    "stress / burnout",
    "sleep disruption",
    "loneliness / social withdrawal",
    "mood fluctuation signs",
    "trauma-related stress signs",
    "obsessive / repetitive worry signs",
    "eating / body image concerns",
    "substance / coping concerns",
    "irritability / anger",
    "concentration / cognitive fog",
    "grief / loss",
    "attention / restlessness signs",
    "self-harm / suicidal crisis signs",
    "unusual perception / reality-stress signs",
    "relationship / interpersonal distress",
    "academic / work pressure",
    "general emotional strain",
]

SYSTEM_PROMPT = f"""You are TrustMind AI, an early-sign wellbeing support assistant for students.

GOAL
Read ANY free-form user message and detect possible EARLY SIGNS of mental-health-related
distress across many wellbeing areas. Users may write casually, with slang, typos,
short texts, long vents, mixed emotions, or positive/neutral notes.

You must try to notice signs related to ANY of these areas when present:
{chr(10).join(f"- {t}" for t in EARLY_SIGN_TAXONOMY)}

CRITICAL BOUNDARIES
- You are NOT a doctor, psychiatrist, psychologist, or therapist.
- Do NOT diagnose disorders (never say "you have depression/bipolar/OCD/etc.").
- Frame findings as possible early wellbeing signs or themes only.
- Prefer cautious language: "may suggest", "possible early signs of", "themes related to".
- If evidence is weak or ambiguous, raise uncertainty and keep concern lower.
- If the message is mostly positive/neutral with no distress signs, say so and keep concern Low.
- If self-harm or suicidal crisis language appears: concern_level=High,
  abstention_status="Abstention triggered — no clinical prediction",
  include "self-harm / suicidal crisis signs" in early_signs, and prioritise crisis steps.
- Cover diverse presentations: anxiety, low mood, burnout, sleep issues, panic, loneliness,
  mood swings, trauma stress, obsessive worry, eating concerns, substance coping, grief,
  attention difficulties, interpersonal distress, academic pressure, and more when present.
- A single message can contain MULTIPLE early signs — list all that are reasonably supported.

Return ONLY valid JSON with exactly these keys:
{{
  "concern_level": "Low" | "Moderate" | "High",
  "ai_confidence": "e.g. \\"76%\\"",
  "uncertainty_level": "Low" | "Medium" | "High",
  "grounding_status": "short status string",
  "abstention_status": "Prediction accepted" | "Abstention triggered — no clinical prediction",
  "explanation": "2-4 sentences: what early signs you noticed, without diagnosing",
  "early_signs": ["list of matching themes from the taxonomy above, or closely worded equivalents"],
  "safe_next_steps": ["3-5 practical, non-clinical next steps"]
}}
"""


def _build_user_prompt(text: str, retrieved_context: str = "") -> str:
    context_block = ""
    if retrieved_context.strip():
        context_block = f"""
Retrieved trusted guidance (use for safe next steps and grounding only; do NOT diagnose):
\"\"\"
{retrieved_context}
\"\"\"
"""
    return f"""Perform early-sign wellbeing detection on this user message.
{context_block}
User message:
\"\"\"
{text}
\"\"\"
"""


def _retrieve_context(text: str) -> tuple[str, list[str]]:
    """Optional hybrid retrieval for Mode B (USE_RAG=true)."""
    if not settings.use_rag:
        return "", []
    try:
        from pathlib import Path
        import sys

        root = Path(__file__).resolve().parents[3]
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from rag.retriever import HybridRetriever

        passages = HybridRetriever().retrieve(text, top_k=settings.rag_top_k)
        if not passages:
            return "", []
        blocks = []
        sources: list[str] = []
        for i, p in enumerate(passages, start=1):
            sources.append(p.source)
            blocks.append(
                f"[{i}] {p.organisation} — {p.title}\n{p.text[:800]}"
            )
        return "\n\n".join(blocks), sources
    except Exception as exc:  # noqa: BLE001 — fall back to non-RAG analyse
        logger.warning("RAG retrieval unavailable (%s); continuing without context", exc)
        return "", []


def _extract_json(text: str) -> dict[str, Any] | None:
    if not text or not str(text).strip():
        return None
    cleaned = str(text).strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def _normalise_result(data: dict[str, Any]) -> AnalyseResult:
    concern = str(data.get("concern_level", "Low")).strip().title()
    if concern not in VALID_CONCERN:
        concern = "Moderate"

    uncertainty = str(data.get("uncertainty_level", "Medium")).strip().title()
    if uncertainty not in VALID_UNCERTAINTY:
        uncertainty = "Medium"

    abstention = str(data.get("abstention_status", "Prediction accepted")).strip()
    if abstention not in VALID_ABSTENTION:
        if "abstention" in abstention.lower() or concern == "High":
            abstention = "Abstention triggered — no clinical prediction"
        else:
            abstention = "Prediction accepted"

    confidence = str(data.get("ai_confidence", "70%")).strip()
    if not re.search(r"\d", confidence):
        confidence = "70%"
    if "%" not in confidence:
        confidence = f"{confidence}%"

    explanation = str(data.get("explanation", "")).strip()
    if not explanation:
        explanation = (
            "I looked for possible early wellbeing signs in your message. "
            "This is not a diagnosis. If things feel heavy, support can help."
        )

    grounding = str(
        data.get(
            "grounding_status",
            "Early-sign wellbeing assessment (non-diagnostic)",
        )
    ).strip()

    # Accept either early_signs or themes from older prompt variants
    early_signs = _as_str_list(data.get("early_signs")) or _as_str_list(data.get("themes"))
    if not early_signs and concern != "Low":
        early_signs = ["general emotional strain"]

    steps = _as_str_list(data.get("safe_next_steps"))
    if not steps:
        steps = [
            "Take a short break and notice how you feel",
            "Consider speaking to someone you trust",
            "Explore UWE wellbeing support if you are a student",
        ]
    if concern == "High" or any("suicid" in s.lower() or "self-harm" in s.lower() for s in early_signs):
        crisis_steps = [
            "If you are in immediate danger, contact emergency services",
            "Reach out to Samaritans on 116 123 (UK) or local crisis support",
            "Speak to a trusted person or UWE wellbeing support",
        ]
        steps = crisis_steps + [s for s in steps if s not in crisis_steps]

    return AnalyseResult(
        concern_level=concern,
        ai_confidence=confidence,
        uncertainty_level=uncertainty,
        grounding_status=grounding,
        abstention_status=abstention,
        explanation=explanation,
        safe_next_steps=steps[:5],
        safety_note=SAFETY_NOTE,
        early_signs=early_signs[:8],
    )


def llm_available() -> bool:
    return bool(settings.openai_api_key) and settings.analyse_backend in {
        "llm",
        "auto",
    }


def run_llm_analysis(request: AnalyseRequest) -> AnalyseResult:
    """Call OpenAI for broad early-sign wellbeing detection (Mode A or Mode B)."""
    from openai import OpenAI

    retrieved_context, source_ids = _retrieve_context(request.text)
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _build_user_prompt(request.text, retrieved_context),
            },
        ],
    )
    content = response.choices[0].message.content or ""
    parsed = _extract_json(content)
    if parsed is None:
        raise ValueError("LLM returned invalid JSON")
    if source_ids:
        parsed["grounding_status"] = (
            f"RAG-grounded early-sign assessment using: {', '.join(source_ids[:5])}"
        )
    elif settings.use_rag:
        parsed.setdefault(
            "grounding_status",
            "USE_RAG enabled but no passages retrieved; LLM-only fallback",
        )
    return _normalise_result(parsed)
