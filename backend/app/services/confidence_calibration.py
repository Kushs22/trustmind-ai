"""
Evidence-based confidence calibration for TrustMind analyse.

Combines retrieval quality, source agreement, LLM self-report, multi-run
consistency, and retrieval coverage into a single calibrated confidence.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Sequence

logger = logging.getLogger(__name__)

# Fixed dissertation weights (must sum to 1.0)
W_RETRIEVAL_SIMILARITY = 0.30
W_SOURCE_AGREEMENT = 0.20
W_LLM_CONFIDENCE = 0.20
W_CLASSIFICATION_CONSISTENCY = 0.20
W_RETRIEVAL_COVERAGE = 0.10

LABEL_HINTS: dict[str, tuple[str, ...]] = {
    "depression": (
        "depression",
        "depressive",
        "low mood",
        "low-mood",
        "sadness",
        "lonely",
        "loneliness",
        "exhaust",
        "burnout",
    ),
    "anxiety": (
        "anxiety",
        "anxious",
        "panic",
        "worry",
        "worried",
        "phobia",
        "stress",
        "exam",
        "student",
    ),
    "suicidewatch": (
        "suicid",
        "crisis",
        "self-harm",
        "self harm",
        "urgent help",
        "ending your life",
    ),
    "bipolar": ("bipolar", "mania", "manic", "hypomania"),
    "offmychest": (
        "wellbeing",
        "well-being",
        "general",
        "student life",
        "burnout",
        "lonely",
        "loneliness",
        "exhaust",
        "stress",
    ),
}


@dataclass(frozen=True)
class ConfidenceBreakdown:
    """Component scores on a 0–100 scale (retrieval fields null in LLM-only mode)."""

    retrieval_similarity: int | None
    source_agreement: int | None
    llm_confidence: int
    classification_consistency: int
    retrieval_coverage: int | None
    input_clarity: int | None = None

    def to_dict(self) -> dict[str, int | None]:
        return asdict(self)


@dataclass(frozen=True)
class CalibratedConfidence:
    """Final calibrated score plus explainable components."""

    confidence: float  # 0–1 for abstention threshold
    confidence_pct: int  # 0–100 for display / API examples
    breakdown: ConfidenceBreakdown
    uncertainty: str
    weights_used: dict[str, float]
    notes: str = ""

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "calibrated_confidence": round(self.confidence, 4),
            "calibrated_confidence_pct": self.confidence_pct,
            "uncertainty": self.uncertainty,
            "confidence_breakdown": self.breakdown.to_dict(),
            "weights_used": self.weights_used,
            "notes": self.notes,
        }


def uncertainty_from_confidence(confidence: float) -> str:
    """
    Map calibrated confidence (0–1) to uncertainty labels.

    90–100 Very Low | 75–89 Low | 60–74 Medium | 45–59 High | <45 Very High
    """
    pct = _to_pct(confidence)
    if pct >= 90:
        return "Very Low"
    if pct >= 75:
        return "Low"
    if pct >= 60:
        return "Medium"
    if pct >= 45:
        return "High"
    return "Very High"


def _to_pct(value: float) -> int:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0
    if v <= 1.0:
        v *= 100.0
    return int(max(0, min(100, round(v))))


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _normalise_label(label: str | None) -> str:
    if not label:
        return ""
    key = str(label).strip().lower().replace(" ", "")
    aliases = {
        "self.depression": "depression",
        "self.anxiety": "anxiety",
        "self.suicidewatch": "suicidewatch",
        "self.bipolar": "bipolar",
        "self.offmychest": "offmychest",
        "anxiety": "anxiety",
        "depression": "depression",
        "suicidewatch": "suicidewatch",
        "bipolar": "bipolar",
        "offmychest": "offmychest",
    }
    return aliases.get(key, key)


def _passage_blob(passage: dict[str, Any] | Any) -> str:
    if hasattr(passage, "to_dict"):
        passage = passage.to_dict()
    if not isinstance(passage, dict):
        return str(passage).lower()
    parts = [
        str(passage.get("source") or ""),
        str(passage.get("title") or ""),
        str(passage.get("topic") or ""),
        str(passage.get("organisation") or ""),
        str(passage.get("text") or "")[:800],
    ]
    return " ".join(parts).lower()


def _passage_supports_label(passage: dict[str, Any] | Any, label: str) -> bool:
    norm = _normalise_label(label)
    if not norm:
        return False
    hints = LABEL_HINTS.get(norm, ())
    blob = _passage_blob(passage)
    return any(h in blob for h in hints)


def score_retrieval_similarity(
    passages: Sequence[dict[str, Any] | Any],
) -> float:
    """
    Average retrieval strength of retrieved chunks (0–1).

    Prefers FAISS/cosine similarity when present. BM25-only runs previously fell
    back to raw RRF ranks (~0.01–0.02), which falsely tanked calibrated
    confidence and triggered abstention even when strong lexical hits existed.
    """
    if not passages:
        return 0.0
    dense_scores: list[float] = []
    bm25_scores: list[float] = []
    soft_scores: list[float] = []
    for p in passages:
        d = p.to_dict() if hasattr(p, "to_dict") else dict(p) if isinstance(p, dict) else {}
        try:
            faiss = float(d.get("faiss_score") or 0.0)
        except (TypeError, ValueError):
            faiss = 0.0
        if faiss > 0.0:
            dense_scores.append(_clamp01(faiss))
            continue
        try:
            bm25 = float(d.get("bm25_score") or 0.0)
        except (TypeError, ValueError):
            bm25 = 0.0
        if bm25 > 0.0:
            bm25_scores.append(bm25)
            continue
        try:
            soft_scores.append(_clamp01(float(d.get("similarity_score") or 0.0)))
        except (TypeError, ValueError):
            continue

    scores: list[float] = list(dense_scores)
    if bm25_scores:
        peak = max(bm25_scores) or 1.0
        # Any positive BM25 hit is at least a moderate signal; best hit → 1.0.
        scores.extend(_clamp01(0.50 + 0.50 * (s / peak)) for s in bm25_scores)
    scores.extend(s for s in soft_scores if s > 0)
    if not scores:
        # Passages present but unscored — treat as weak-but-real retrieval.
        return 0.45 if passages else 0.0
    return sum(scores) / len(scores)


def score_source_agreement(
    passages: Sequence[dict[str, Any] | Any],
    prediction: str | None,
) -> float:
    """
    Fraction of distinct retrieved sources whose content supports the prediction.
    """
    if not passages or not prediction:
        return 0.0
    by_source: dict[str, list[Any]] = {}
    for p in passages:
        d = p.to_dict() if hasattr(p, "to_dict") else dict(p) if isinstance(p, dict) else {}
        sid = str(d.get("source") or d.get("chunk_id") or "").strip() or "unknown"
        by_source.setdefault(sid, []).append(p)
    if not by_source:
        return 0.0
    agreeing = sum(
        1
        for items in by_source.values()
        if any(_passage_supports_label(item, prediction) for item in items)
    )
    return agreeing / len(by_source)


def score_classification_consistency(labels: Sequence[str | None]) -> float:
    """Share of runs that match the majority label (0–1)."""
    normalised = [_normalise_label(x) for x in labels if _normalise_label(x)]
    if not normalised:
        return 0.0
    if len(normalised) == 1:
        return 1.0
    _label, count = Counter(normalised).most_common(1)[0]
    return count / len(normalised)


def score_retrieval_coverage(
    passages: Sequence[dict[str, Any] | Any],
    *,
    expected_k: int,
) -> float:
    """
    Higher when enough relevant context was retrieved.

    Combines fill-rate (n / expected_k) with mean similarity so a single weak
    document scores low.
    """
    expected = max(1, int(expected_k))
    n = len(passages)
    if n == 0:
        return 0.0
    fill = min(1.0, n / expected)
    mean_sim = score_retrieval_similarity(passages)
    # One weak hit → low; full top-k with solid similarity → high
    return _clamp01(0.55 * fill + 0.45 * mean_sim)


def majority_label(labels: Sequence[str | None]) -> str | None:
    normalised = [_normalise_label(x) for x in labels if _normalise_label(x)]
    if not normalised:
        return None
    winner, _ = Counter(normalised).most_common(1)[0]
    # Restore canonical casing used by the product
    canon = {
        "depression": "depression",
        "anxiety": "Anxiety",
        "suicidewatch": "SuicideWatch",
        "bipolar": "bipolar",
        "offmychest": "offmychest",
    }
    return canon.get(winner, winner)


# Standalone LLM weights (must not reuse RAG formula)
W_LLM_ONLY_SELF = 0.40
W_LLM_ONLY_CONSISTENCY = 0.40
W_LLM_ONLY_CLARITY = 0.20

CAP_NORMAL = 0.90
CAP_AMBIGUOUS = 0.75
CAP_INCONSISTENT = 0.60
AMBIGUITY_SUBSTANTIAL = 0.45


def score_input_ambiguity(text: str, run_labels: Sequence[str | None] | None = None) -> float:
    """
    Estimate input ambiguity in [0, 1] (higher = more ambiguous).

    Considers short/underspecified text, contradictions, overlapping class cues,
    missing duration/context, and ordinary non-clinical experiences.
    """
    raw = (text or "").strip()
    t = raw.lower()
    words = t.split()
    score = 0.0

    # Insufficient detail
    if len(words) < 12:
        score += 0.35
    elif len(words) < 25:
        score += 0.15

    # Contradictory statements
    positive_cues = (
        "feel fine",
        "feeling fine",
        "i'm fine",
        "im fine",
        "great",
        "happy",
        "brilliant",
        "motivated",
        "okay today",
        "feeling good",
    )
    negative_cues = (
        "but ",
        "however",
        "although",
        "empty",
        "hopeless",
        "anxious",
        "depressed",
        "die",
        "disappear",
        "without me",
        "can't stop",
        "cant stop",
    )
    if any(p in t for p in positive_cues) and any(n in t for n in negative_cues):
        score += 0.25

    # Overlapping class indicators.
    # Long first-person check-ins routinely mention several feelings; penalise lightly.
    class_hits = 0
    for hints in LABEL_HINTS.values():
        if any(h in t for h in hints):
            class_hits += 1
    long_rich = len(words) >= 80
    if class_hits >= 3:
        score += 0.10 if long_rich else 0.25
    elif class_hits == 2:
        score += 0.05 if long_rich else 0.15

    # Lack of duration or context
    duration_cues = (
        "day",
        "days",
        "week",
        "weeks",
        "month",
        "months",
        "year",
        "years",
        "since",
        "always",
        "often",
        "recently",
        "several",
        "lately",
    )
    if not any(d in t for d in duration_cues) and len(words) < 40:
        score += 0.15

    # Ordinary experiences that need not indicate a wellbeing concern
    ordinary = (
        "tired",
        "annoyed",
        "vent",
        "weekend",
        "laptop",
        "battery",
        "hungry",
        "busy",
        "flatmate",
        "roommate",
        "traffic",
    )
    if any(o in t for o in ordinary) and class_hits <= 1 and len(words) < 35:
        score += 0.20

    # Disagreement across runs also signals ambiguity (softer on long narratives)
    if run_labels:
        norms = {_normalise_label(x) for x in run_labels if _normalise_label(x)}
        if len(norms) > 1:
            score += 0.08 if long_rich else 0.15

    # Detailed first-person emotional narratives are usually clearer, not murkier.
    if long_rich and any(
        cue in t
        for cue in (
            "i feel",
            "i've been",
            "ive been",
            "lonely",
            "heartbroken",
            "anxious",
            "worried",
            "empty",
            "stuck",
        )
    ):
        score = max(0.0, score - 0.15)

    return _clamp01(score)


def calibrate_llm_only_confidence(
    *,
    text: str,
    prediction: str | None,
    llm_confidence: float,
    run_labels: Sequence[str | None],
) -> CalibratedConfidence:
    """
    Standalone LLM confidence — does not use retrieval signals.

    overall = 0.40 * llm_confidence
            + 0.40 * classification_consistency
            + 0.20 * input_clarity

    Caps:
      - max 90% for normal classifications
      - max 75% when input has substantial ambiguity
      - max 60% when repeated-run predictions differ
    """
    llm_c = _clamp01(llm_confidence if llm_confidence <= 1.0 else llm_confidence / 100.0)
    consistency = score_classification_consistency(run_labels)
    ambiguity = score_input_ambiguity(text, run_labels)
    clarity = _clamp01(1.0 - ambiguity)

    overall = (
        W_LLM_ONLY_SELF * llm_c
        + W_LLM_ONLY_CONSISTENCY * consistency
        + W_LLM_ONLY_CLARITY * clarity
    )

    predictions_differ = len({_normalise_label(x) for x in run_labels if _normalise_label(x)}) > 1
    substantial_ambiguity = ambiguity >= AMBIGUITY_SUBSTANTIAL
    long_rich = len((text or "").split()) >= 80

    cap = CAP_NORMAL
    if substantial_ambiguity:
        cap = min(cap, CAP_AMBIGUOUS)
    if predictions_differ:
        # Long emotional check-ins often flip between close themes (e.g. depression /
        # offmychest); keep a usable label rather than collapsing under 0.45.
        inconsist_cap = 0.70 if long_rich else CAP_INCONSISTENT
        cap = min(cap, inconsist_cap)
    overall = min(_clamp01(overall), cap)

    # Floor for rich narratives with a usable majority label so product UX does not
    # immediately abstain when the model is only mid-uncertain.
    if (
        prediction
        and long_rich
        and consistency >= (2 / 3)
        and overall < 0.50
        and llm_c >= 0.45
    ):
        overall = 0.50

    weights = {
        "llm_confidence": W_LLM_ONLY_SELF,
        "classification_consistency": W_LLM_ONLY_CONSISTENCY,
        "input_clarity": W_LLM_ONLY_CLARITY,
        "retrieval_similarity": 0.0,
        "source_agreement": 0.0,
        "retrieval_coverage": 0.0,
    }
    notes = (
        f"llm_only_formula clarity={clarity:.2f} ambiguity={ambiguity:.2f} "
        f"cap={cap:.2f} differ={predictions_differ}"
    )
    breakdown = ConfidenceBreakdown(
        retrieval_similarity=None,
        source_agreement=None,
        llm_confidence=_to_pct(llm_c),
        classification_consistency=_to_pct(consistency),
        retrieval_coverage=None,
        input_clarity=_to_pct(clarity),
    )
    result = CalibratedConfidence(
        confidence=overall,
        confidence_pct=_to_pct(overall),
        breakdown=breakdown,
        uncertainty=uncertainty_from_confidence(overall),
        weights_used={k: round(v, 4) for k, v in weights.items()},
        notes=notes,
    )
    logger.info(
        "llm_only_calibration prediction=%s overall=%s breakdown=%s notes=%s",
        prediction,
        result.confidence_pct,
        breakdown.to_dict(),
        notes,
    )
    return result


def calibrate_confidence(
    *,
    passages: Sequence[dict[str, Any] | Any],
    prediction: str | None,
    llm_confidence: float,
    run_labels: Sequence[str | None],
    expected_k: int,
    has_retrieval: bool = True,
    text: str = "",
) -> CalibratedConfidence:
    """
    Weighted calibrated confidence.

    RAG path uses hybrid retrieval weights. Standalone LLM path uses
    calibrate_llm_only_confidence (never reuses RAG retrieval weights).
    """
    if not has_retrieval or not passages:
        return calibrate_llm_only_confidence(
            text=text,
            prediction=prediction,
            llm_confidence=llm_confidence,
            run_labels=run_labels,
        )

    retrieval_similarity = score_retrieval_similarity(passages)
    source_agreement = score_source_agreement(passages, prediction)
    llm_c = _clamp01(llm_confidence if llm_confidence <= 1.0 else llm_confidence / 100.0)
    consistency = score_classification_consistency(run_labels)
    coverage = score_retrieval_coverage(passages, expected_k=expected_k)

    weights = {
        "retrieval_similarity": W_RETRIEVAL_SIMILARITY,
        "source_agreement": W_SOURCE_AGREEMENT,
        "llm_confidence": W_LLM_CONFIDENCE,
        "classification_consistency": W_CLASSIFICATION_CONSISTENCY,
        "retrieval_coverage": W_RETRIEVAL_COVERAGE,
    }
    notes = "full_hybrid_weights"
    overall = (
        weights["retrieval_similarity"] * retrieval_similarity
        + weights["source_agreement"] * source_agreement
        + weights["llm_confidence"] * llm_c
        + weights["classification_consistency"] * consistency
        + weights["retrieval_coverage"] * coverage
    )

    overall = _clamp01(overall)
    breakdown = ConfidenceBreakdown(
        retrieval_similarity=_to_pct(retrieval_similarity),
        source_agreement=_to_pct(source_agreement),
        llm_confidence=_to_pct(llm_c),
        classification_consistency=_to_pct(consistency),
        retrieval_coverage=_to_pct(coverage),
        input_clarity=None,
    )
    result = CalibratedConfidence(
        confidence=overall,
        confidence_pct=_to_pct(overall),
        breakdown=breakdown,
        uncertainty=uncertainty_from_confidence(overall),
        weights_used={k: round(v, 4) for k, v in weights.items()},
        notes=notes,
    )
    logger.info(
        "confidence_calibration prediction=%s overall=%s breakdown=%s weights=%s notes=%s",
        prediction,
        result.confidence_pct,
        breakdown.to_dict(),
        result.weights_used,
        notes,
    )
    return result
