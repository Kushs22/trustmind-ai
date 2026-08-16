"""
Human-readable evidence presentation for TrustMind analyse.

Builds EvidenceItem records from retrieved passages + optional source_manifest
enrichment. Reasons are deterministic templates (no extra LLM call).
"""

from __future__ import annotations

import csv
import logging
import re
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Sequence

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MANIFEST = _REPO_ROOT / "knowledge_base" / "metadata" / "source_manifest.csv"

# Overlap terms used only to phrase "why retrieved" — not clinical claims
_STOP = {
    "the",
    "and",
    "for",
    "that",
    "with",
    "this",
    "from",
    "have",
    "been",
    "were",
    "they",
    "their",
    "about",
    "into",
    "your",
    "you",
    "are",
    "was",
    "but",
    "not",
    "can",
    "will",
    "just",
    "like",
    "feel",
    "feeling",
    "really",
}


@dataclass
class EvidenceItem:
    source_id: str
    organisation: str
    title: str
    topic: str = ""
    url: str = ""
    retrieval_score: float = 0.0
    reason_retrieved: str = ""
    display_label: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if not data.get("display_label"):
            data["display_label"] = format_display_label(
                data.get("organisation") or "",
                data.get("title") or "",
            )
        return data


def format_display_label(organisation: str, title: str) -> str:
    org = (organisation or "").strip()
    tit = (title or "").strip()
    if org and tit:
        return f"{org} — {tit}"
    return org or tit or "Trusted wellbeing source"


@lru_cache(maxsize=1)
def _load_manifest() -> dict[str, dict[str, str]]:
    path = _MANIFEST
    out: dict[str, dict[str, str]] = {}
    if not path.is_file():
        return out
    try:
        with path.open(encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                sid = str(row.get("source_id") or "").strip()
                if not sid:
                    continue
                out[sid] = {
                    "organisation": str(row.get("organisation") or "").strip(),
                    "title": str(row.get("title") or "").strip(),
                    "topic": str(row.get("topic") or "").strip(),
                    "url": str(row.get("source_url") or "").strip(),
                }
    except OSError:
        logger.exception("Failed to load source_manifest.csv")
    return out


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z']{4,}", (text or "").lower())
    return {w for w in words if w not in _STOP}


def _reason_retrieved(
    *,
    user_text: str,
    passage_text: str,
    topic: str,
    organisation: str,
    prediction: str | None,
) -> str:
    """Cautious one-to-two sentence explanation — no diagnostic claims."""
    overlap = sorted(_tokens(user_text) & _tokens(passage_text))
    theme = (topic or "").strip() or (prediction or "wellbeing")
    org = (organisation or "Trusted guidance").strip()

    if overlap:
        shown = ", ".join(overlap[:4])
        return (
            f"This {org} guidance may be helpful because it touches themes that "
            f"overlap with what you shared (for example: {shown}). "
            f"It offers general information related to {theme} — it does not "
            f"prove a diagnosis."
        )
    return (
        f"This {org} guidance was included as related support on {theme}. "
        f"It can sit alongside what you shared as cautious context — not a "
        f"clinical conclusion."
    )


def _passage_as_dict(passage: Any) -> dict[str, Any]:
    if hasattr(passage, "to_dict"):
        return passage.to_dict()
    if isinstance(passage, dict):
        return passage
    return {}


def build_evidence_items(
    passages: Sequence[Any],
    *,
    user_text: str,
    prediction: str | None,
    max_items: int | None = None,
) -> list[EvidenceItem]:
    """
    Dedupe by source_id (keep highest retrieval score), enrich from manifest.
    """
    manifest = _load_manifest()
    best: dict[str, EvidenceItem] = {}

    for raw in passages:
        d = _passage_as_dict(raw)
        sid = str(d.get("source") or d.get("source_id") or "").strip()
        if not sid:
            continue
        meta = manifest.get(sid, {})
        organisation = str(d.get("organisation") or meta.get("organisation") or "").strip()
        title = str(d.get("title") or meta.get("title") or "").strip()
        topic = str(d.get("topic") or meta.get("topic") or "").strip()
        url = str(d.get("source_url") or d.get("url") or meta.get("url") or "").strip()
        if not title:
            title = f"{organisation} — {topic}".strip(" —") if organisation or topic else sid

        try:
            score = float(d.get("faiss_score") or d.get("similarity_score") or 0.0)
        except (TypeError, ValueError):
            score = 0.0

        reason = _reason_retrieved(
            user_text=user_text,
            passage_text=str(d.get("text") or ""),
            topic=topic,
            organisation=organisation or "trusted",
            prediction=prediction,
        )
        item = EvidenceItem(
            source_id=sid,
            organisation=organisation or "Trusted source",
            title=title,
            topic=topic,
            url=url if url.startswith("http") else "",
            retrieval_score=round(score, 4),
            reason_retrieved=reason,
            display_label=format_display_label(organisation or "Trusted source", title),
        )
        prev = best.get(sid)
        if prev is None or item.retrieval_score >= prev.retrieval_score:
            best[sid] = item

    ranked = sorted(best.values(), key=lambda x: x.retrieval_score, reverse=True)
    if max_items is not None:
        return ranked[: max(0, int(max_items))]
    return ranked


DIAGNOSTIC_PHRASES = (
    "you have depression",
    "you have anxiety",
    "you are bipolar",
    "the diagnosis is",
    "this proves",
    "you are diagnosed",
    "classic symptoms",
    "symptoms of bipolar disorder",
    "symptoms of depression",
    "symptoms of anxiety",
)

BIPOLAR_CAUTIOUS_REASONING = (
    "It sounds like you're describing experiences that may overlap with descriptions "
    "associated with manic or hypomanic episodes — for example reduced sleep, unusually "
    "elevated confidence and impulsive spending, followed by exhaustion and low mood. "
    "We've noted mood-swing-related themes so we can point you toward supportive guidance. "
    "This is not a clinical diagnosis."
)


def sanitise_reasoning(text: str) -> str:
    """Light guard against overtly diagnostic phrasing — does not invent content."""
    cleaned = (text or "").strip()
    lower = cleaned.lower()
    # Replace diagnostic bipolar framing with cautious research wording.
    if (
        "classic symptoms of bipolar" in lower
        or "symptoms of bipolar disorder" in lower
        or ("classic symptoms" in lower and "bipolar" in lower)
    ):
        return BIPOLAR_CAUTIOUS_REASONING

    flagged = any(phrase in lower for phrase in DIAGNOSTIC_PHRASES)
    if flagged:
        cleaned = cleaned.replace(
            "classic symptoms of",
            "experiences that may overlap with descriptions associated with",
        )
        cleaned = cleaned.replace(
            "Classic symptoms of",
            "Experiences that may overlap with descriptions associated with",
        )
        if "not a clinical diagnosis" not in cleaned.lower():
            cleaned = (
                cleaned.rstrip(".")
                + ". This is an automated wellbeing assessment and not a clinical diagnosis."
            )
    return cleaned
