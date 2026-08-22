"""
Deterministic 0–100 "support urgency" for TrustMind analyse results.

This is NOT a clinical risk, suicide-risk, or diagnostic score. It only
summarises how strongly the existing pipeline suggests seeking support,
using crisis flags, concern level, confidence, themes, and abstention.

Mapping (brief):
  - Crisis / safety path (safety_triggered, SuicideWatch, crisis themes)
    → urgent band, typically 85–100
  - High concern + high confidence → elevated (≈55–84)
  - Moderate concern → moderate (≈35–54)
  - Low / mild concern → low (≈10–34)
  - Abstention / very low confidence without crisis → soft low–mid score
    with uncertain=True (never a confident high "risk" reading)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SupportUrgencyBand = Literal["low", "moderate", "elevated", "urgent"]

_CRISIS_THEME_HINTS = (
    "suicid",
    "self-harm",
    "self harm",
    "crisis",
)


def _is_high_risk_prediction(prediction: str | None) -> bool:
    if not prediction:
        return False
    return prediction.strip().lower() in {"suicidewatch", "self.suicidewatch"}


@dataclass(frozen=True)
class SupportUrgency:
    score: int  # 0–100
    band: SupportUrgencyBand
    rationale: str
    uncertain: bool = False


def _clamp(value: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, value))


def _band_for(score: int) -> SupportUrgencyBand:
    if score >= 85:
        return "urgent"
    if score >= 55:
        return "elevated"
    if score >= 35:
        return "moderate"
    return "low"


def _confidence_0_1(confidence: float) -> float:
    if confidence > 1.0:
        return max(0.0, min(1.0, confidence / 100.0))
    return max(0.0, min(1.0, float(confidence or 0.0)))


def _has_crisis_theme(early_signs: list[str] | None) -> bool:
    blob = " ".join(early_signs or []).lower()
    return any(hint in blob for hint in _CRISIS_THEME_HINTS)


def compute_support_urgency(
    *,
    safety_triggered: bool = False,
    concern_level: str = "Low",
    confidence: float = 0.0,
    status: str = "accepted",
    prediction: str | None = None,
    early_signs: list[str] | None = None,
    support_resources_present: bool = False,
) -> SupportUrgency:
    """
    Pure function: same inputs always yield the same score / band / rationale.
    """
    conf = _confidence_0_1(confidence)
    concern = (concern_level or "Low").strip().title()
    abstained = (status or "").lower() == "abstained"
    crisis = (
        bool(safety_triggered)
        or support_resources_present
        or _is_high_risk_prediction(prediction)
        or _has_crisis_theme(early_signs)
    )

    # --- Crisis / immediate support path: always high band ---
    if crisis:
        score = 88
        if _is_high_risk_prediction(prediction) or _has_crisis_theme(early_signs):
            score = 94
        if safety_triggered or support_resources_present:
            score = max(score, 90)
        score = _clamp(score)
        return SupportUrgency(
            score=score,
            band=_band_for(score),
            rationale=(
                "Priority support options were suggested from what you shared. "
                "This meter reflects how strongly support is suggested — "
                "it is not a diagnosis or clinical risk score."
            ),
            uncertain=False,
        )

    # --- Abstention / uncertain: do not overstate ---
    if abstained:
        # Soft low–mid range scaled lightly by confidence; never elevated/urgent.
        score = _clamp(int(round(18 + conf * 28)), 15, 42)
        return SupportUrgency(
            score=score,
            band=_band_for(score),
            rationale=(
                "We held back a labelled read, so this meter stays softer and "
                "uncertain — not a confident urgency signal. Not a diagnosis."
            ),
            uncertain=True,
        )

    theme_n = len(early_signs or [])
    theme_bump = min(6, theme_n * 2)

    # --- Accepted path by concern + confidence ---
    if concern == "High":
        if conf >= 0.75:
            score = 72 + int(round((conf - 0.75) * 40)) + theme_bump  # ~72–84
        elif conf >= 0.55:
            score = 58 + int(round((conf - 0.55) * 50)) + theme_bump  # ~58–70
        else:
            # Low confidence on a "High" concern label → soften, mark uncertain
            score = _clamp(48 + theme_bump, 40, 54)
            return SupportUrgency(
                score=score,
                band=_band_for(score),
                rationale=(
                    "Concern looks higher, but confidence is limited, so urgency "
                    "stays tempered. Not a diagnosis or clinical risk score."
                ),
                uncertain=True,
            )
        score = _clamp(score, 55, 84)
        return SupportUrgency(
            score=score,
            band=_band_for(score),
            rationale=(
                "Higher concern with clearer confidence suggests checking in "
                "with support sooner. Not a diagnosis or clinical risk score."
            ),
            uncertain=False,
        )

    if concern == "Moderate":
        if conf >= 0.75:
            score = 42 + int(round((conf - 0.75) * 40)) + theme_bump  # ~42–54
        elif conf >= 0.5:
            score = 36 + int(round((conf - 0.5) * 24)) + theme_bump
        else:
            score = 32 + theme_bump
            return SupportUrgency(
                score=_clamp(score, 28, 45),
                band=_band_for(_clamp(score, 28, 45)),
                rationale=(
                    "Some concern themes came through, with limited confidence. "
                    "This is a gentle support nudge — not a diagnosis."
                ),
                uncertain=True,
            )
        score = _clamp(score, 35, 54)
        return SupportUrgency(
            score=score,
            band=_band_for(score),
            rationale=(
                "Moderate concern suggests it may help to use support options "
                "if things feel heavier. Not a diagnosis or clinical risk score."
            ),
            uncertain=False,
        )

    # Low / unknown concern
    if conf < 0.5:
        score = _clamp(12 + int(round(conf * 20)) + theme_bump, 8, 28)
        return SupportUrgency(
            score=score,
            band=_band_for(score),
            rationale=(
                "Signals look milder and confidence is limited, so urgency stays "
                "low. Not a diagnosis or clinical risk score."
            ),
            uncertain=True,
        )

    score = _clamp(14 + int(round(conf * 18)) + theme_bump, 10, 34)
    return SupportUrgency(
        score=score,
        band=_band_for(score),
        rationale=(
            "Milder signals for now — keep an eye on how you feel and use "
            "support if that changes. Not a diagnosis or clinical risk score."
        ),
        uncertain=False,
    )


def band_label(band: SupportUrgencyBand) -> str:
    return {
        "low": "Low",
        "moderate": "Moderate",
        "elevated": "Elevated",
        "urgent": "Urgent",
    }[band]
