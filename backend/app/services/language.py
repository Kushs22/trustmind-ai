"""Language hints for multilingual check-ins.

Safety checks always use the user's original words.
Retrieval may use an English search line so the UK knowledge base can match.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_EN_HINTS = {
    "the",
    "a",
    "and",
    "to",
    "of",
    "i",
    "you",
    "my",
    "is",
    "it",
    "in",
    "for",
    "me",
    "that",
    "this",
    "with",
    "feel",
    "feeling",
    "been",
    "have",
    "not",
    "can't",
    "cant",
    "help",
}

_SCRIPT_HINTS: tuple[tuple[str, tuple[tuple[int, int], ...]], ...] = (
    ("ar", ((0x0600, 0x06FF), (0x0750, 0x077F))),
    ("zh", ((0x4E00, 0x9FFF),)),
    ("hi", ((0x0900, 0x097F),)),
    ("ur", ((0x0600, 0x06FF),)),
    ("ru", ((0x0400, 0x04FF),)),
    ("el", ((0x0370, 0x03FF),)),
    ("he", ((0x0590, 0x05FF),)),
    ("th", ((0x0E00, 0x0E7F),)),
    ("ko", ((0xAC00, 0xD7AF),)),
    ("ja", ((0x3040, 0x30FF),)),
)


def _has_letter_in(text: str, ranges: tuple[tuple[int, int], ...]) -> bool:
    for ch in text:
        code = ord(ch)
        for start, end in ranges:
            if start <= code <= end:
                return True
    return False


def detect_script_hint(text: str) -> str:
    """Best-effort script/language hint. Unknown Latin stays 'und'."""
    blob = text or ""
    for code, ranges in _SCRIPT_HINTS:
        if _has_letter_in(blob, ranges):
            return code
    return "und"


def likely_english(text: str) -> bool:
    blob = text or ""
    if _has_letter_in(blob, tuple(r for _, ranges in _SCRIPT_HINTS for r in ranges)):
        return False
    words = re.findall(r"[A-Za-z']+", blob.lower())
    if not words:
        return False
    hits = sum(1 for w in words if w in _EN_HINTS)
    if len(words) <= 4:
        return hits >= 1
    return hits >= 2


def english_search_query(text: str) -> str:
    """English line for BM25/FAISS only. Never used as the user-facing reply."""
    original = (text or "").strip()
    if not original or likely_english(original):
        return original
    try:
        from app.services.llm_provider import complete_json, llm_configured

        if not llm_configured():
            return original
        raw, err, _provider = complete_json(
            system=(
                "Translate the user's message into plain English for search. "
                "Keep meaning, including slang and distress. "
                "Return JSON only: {\"english\": \"...\"}."
            ),
            user=original[:4000],
            temperature=0.0,
            max_tokens=220,
        )
        if err or not raw:
            return original
        import json

        data = json.loads(raw)
        english = str(data.get("english") or "").strip()
        return english or original
    except Exception:  # noqa: BLE001
        logger.warning("Search translation skipped; using original text")
        return original
