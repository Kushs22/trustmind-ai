"""
Trust signals and grounding status for TrustMind analyse responses.

Formulas (documented for the dissertation README):

  model_confidence   = calibrated confidence on a 0–100 scale
  evidence_strength  = round(0.6 * source_agreement + 0.4 * classification_consistency)
  retrieval_quality  = round(0.6 * retrieval_similarity + 0.4 * retrieval_coverage)

LLM-only / no passages: evidence_strength and retrieval_quality are None (N/A).

Grounding status thresholds (config):
  grounded       — RAG with retrieval_quality >= min AND evidence_strength >= min
  limited        — RAG ran but scores below thresholds, or thin context
  ungrounded     — RAG path with no useful retrieved context
  not_applicable — standalone LLM mode
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.services.confidence_calibration import ConfidenceBreakdown


GROUNDING_LABELS: dict[str, str] = {
    "grounded": "Grounded with retrieved evidence",
    "limited": "Limited supporting evidence",
    "ungrounded": "Standalone model response",  # overridden for RAG empty below
    "not_applicable": "Standalone model response",
}

RAG_UNGROUNDED_LABEL = "Limited supporting evidence"


@dataclass(frozen=True)
class TrustSignals:
    model_confidence: int
    evidence_strength: int | None
    retrieval_quality: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_confidence": self.model_confidence,
            "evidence_strength": self.evidence_strength,
            "retrieval_quality": self.retrieval_quality,
        }


@dataclass(frozen=True)
class GroundingInfo:
    status: str
    label: str

    def to_dict(self) -> dict[str, str]:
        return {"status": self.status, "label": self.label}


def _clamp_pct(value: float | int) -> int:
    return int(max(0, min(100, round(float(value)))))


def compute_trust_signals(
    *,
    calibrated_pct: int,
    breakdown: ConfidenceBreakdown | dict[str, int] | None,
    has_retrieval: bool,
) -> TrustSignals:
    """
    Map calibration components into the three user-facing trust signals.
    """
    model = _clamp_pct(calibrated_pct)
    if not has_retrieval or breakdown is None:
        return TrustSignals(
            model_confidence=model,
            evidence_strength=None,
            retrieval_quality=None,
        )

    if isinstance(breakdown, ConfidenceBreakdown):
        bd = breakdown.to_dict()
    else:
        bd = dict(breakdown)

    sa = bd.get("source_agreement")
    cc = bd.get("classification_consistency")
    rs = bd.get("retrieval_similarity")
    rc = bd.get("retrieval_coverage")
    # Null retrieval fields mean N/A (standalone LLM path) — never coerce to 0.
    if sa is None or rs is None or rc is None:
        return TrustSignals(
            model_confidence=model,
            evidence_strength=None,
            retrieval_quality=None,
        )

    evidence = _clamp_pct(0.6 * float(sa) + 0.4 * float(cc or 0))
    retrieval = _clamp_pct(0.6 * float(rs) + 0.4 * float(rc))
    return TrustSignals(
        model_confidence=model,
        evidence_strength=evidence,
        retrieval_quality=retrieval,
    )


def resolve_grounding(
    *,
    pipeline_used: str,
    has_passages: bool,
    trust: TrustSignals,
) -> GroundingInfo:
    """
    Evidence-based grounding label — not merely whether RAG was invoked.
    """
    is_rag = "RAG" in (pipeline_used or "").upper()
    if not is_rag:
        return GroundingInfo(
            status="not_applicable",
            label=GROUNDING_LABELS["not_applicable"],
        )

    rq_min = int(settings.grounding_retrieval_quality_min)
    ev_min = int(settings.grounding_evidence_strength_min)

    if not has_passages:
        return GroundingInfo(status="ungrounded", label=RAG_UNGROUNDED_LABEL)

    rq = trust.retrieval_quality if trust.retrieval_quality is not None else 0
    ev = trust.evidence_strength if trust.evidence_strength is not None else 0

    if rq >= rq_min and ev >= ev_min:
        return GroundingInfo(status="grounded", label=GROUNDING_LABELS["grounded"])
    if rq > 0 or ev > 0:
        return GroundingInfo(status="limited", label=GROUNDING_LABELS["limited"])
    return GroundingInfo(status="ungrounded", label=RAG_UNGROUNDED_LABEL)


PREDICTION_DISPLAY: dict[str, str] = {
    "depression": "It sounds like low mood may be weighing on you",
    "anxiety": "It sounds like stress or worry has been weighing on you",
    "suicidewatch": (
        "I'm really sorry you're feeling this way — please get support now"
    ),
    "bipolar": "It sounds like your mood or energy has felt up-and-down lately",
    "offmychest": "It sounds like something's been sitting heavy on your mind",
}


def prediction_display_name(prediction: str | None) -> str | None:
    if not prediction:
        return None
    key = prediction.strip().lower().replace(" ", "").replace("self.", "")
    return PREDICTION_DISPLAY.get(key, prediction)
