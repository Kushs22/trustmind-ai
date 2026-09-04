"""Lexical query enrichment so BM25 matches common student wellbeing phrasing."""

from __future__ import annotations

# Cue → extra BM25 terms (curated KB vocabulary: stress, burnout, loneliness, exams).
_ENRICHMENT_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (
        ("exhaust", "tired", "fatigue", "drained", "burnout", "burnt out", "burned out"),
        ("burnout", "stress", "student", "exhausted"),
    ),
    (
        ("lonely", "loneliness", "alone", "isolated", "isolation"),
        ("loneliness", "lonely", "student", "belonging"),
    ),
    (
        (
            "exam",
            "exams",
            "revision",
            "coursework",
            "dissertation",
            "studying",
            "university",
            "assignment",
        ),
        ("exam", "stress", "student", "anxiety", "study"),
    ),
    (
        ("stress", "stressed", "overwhelm", "pressure", "can't focus", "cant focus"),
        ("stress", "anxiety", "student"),
    ),
    (
        (
            "low mood",
            "depressed",
            "depression",
            "hopeless",
            "empty",
            "numb",
            "sad",
        ),
        ("low mood", "depression", "student", "adults"),
    ),
    (
        ("anxious", "anxiety", "worry", "worried", "panic", "chest feels tight"),
        ("anxiety", "worry", "panic", "stress"),
    ),
)


def enrich_wellbeing_query(query: str) -> str:
    """
    Append a few KB-aligned terms for student stress / fatigue / loneliness.

    Keeps the original wording first so BM25 still rewards exact overlap, then
    adds a short cue bag so paraphrases still retrieve NHS / Student Minds /
    YoungMinds guidance.
    """
    raw = (query or "").strip()
    if not raw:
        return raw
    lower = raw.lower()
    extras: list[str] = []
    for cues, terms in _ENRICHMENT_RULES:
        if any(cue in lower for cue in cues):
            extras.extend(terms)
    if not extras:
        return raw
    # Preserve order, drop duplicates already present in the query.
    seen = set(lower.split())
    unique: list[str] = []
    for term in extras:
        key = term.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(term)
    if not unique:
        return raw
    return f"{raw} {' '.join(unique)}"
