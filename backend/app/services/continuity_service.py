"""Pick-up-where-you-left-off continuity from recent saved check-ins.

Only for authenticated (non-anonymous) users who opt in and are not in private mode.
Prior check-ins are loaded server-side — clients never supply history text.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC

from sqlalchemy.orm import Session

from app.models import CheckIn, User
from app.schemas.analyse import AnalyseRequest

# Last N non-private saved check-ins used for continuity (not a full chat thread).
CONTINUITY_CHECKIN_LIMIT = 5
_PREVIEW_MAX = 160
_EXPLANATION_FALLBACK_MAX = 120


@dataclass(frozen=True)
class PriorCheckInSummary:
    date: str
    concern: str
    preview: str
    abstained: bool


def should_use_continuity(user: User | None, payload: AnalyseRequest) -> bool:
    """Login + save-mode continuity only; never for anonymous or private analyse."""
    if user is None or getattr(user, "is_anonymous", False):
        return False
    if not payload.use_past_checkins:
        return False
    if payload.analyse_privately:
        return False
    return True


def _format_date(dt) -> str:
    return dt.astimezone(UTC).strftime("%d %b %Y")


def _clip(text: str, max_len: int) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3] + "..."


def fetch_prior_checkins(
    db: Session,
    user: User,
    *,
    limit: int = CONTINUITY_CHECKIN_LIMIT,
) -> list[PriorCheckInSummary]:
    """Load recent non-private check-ins that still have a text signal."""
    rows = (
        db.query(CheckIn)
        .filter(
            CheckIn.user_id == user.id,
            CheckIn.is_private.is_(False),
        )
        .order_by(CheckIn.created_at.desc())
        .limit(max(1, min(limit, CONTINUITY_CHECKIN_LIMIT)))
        .all()
    )
    out: list[PriorCheckInSummary] = []
    for row in rows:
        preview = (row.text_preview or "").strip()
        if not preview and row.explanation:
            preview = _clip(row.explanation, _EXPLANATION_FALLBACK_MAX)
        if not preview:
            continue
        out.append(
            PriorCheckInSummary(
                date=_format_date(row.created_at),
                concern=(row.concern_level or "Unknown").strip() or "Unknown",
                preview=_clip(preview, _PREVIEW_MAX),
                abstained=bool(row.abstained),
            )
        )
    return out


def format_continuity_block(entries: list[PriorCheckInSummary]) -> str:
    """Short prompt block for LLM/RAG reflection continuity."""
    if not entries:
        return ""
    lines = [
        "Prior check-ins (for continuity only — not a diagnosis record):",
    ]
    for i, entry in enumerate(entries, start=1):
        theme = entry.concern
        if entry.abstained:
            theme = f"{theme} (no label given)"
        lines.append(
            f"{i}. [{entry.date}] Theme/concern: {theme}. "
            f"User shared (summary): {entry.preview}"
        )
    lines.append(
        "Continuity rules: Acknowledge continuity warmly if relevant "
        '(e.g. "last time you mentioned…"). Do not over-quote. '
        "If the new message conflicts with older ones, prioritise the current message. "
        "Do not guilt the user for gaps, changes, or not following up. "
        "Never invent clinical diagnoses from prior check-ins. "
        "Crisis / safety signals in the CURRENT message always take priority."
    )
    return "\n".join(lines)


def load_continuity_context(
    db: Session,
    user: User | None,
    payload: AnalyseRequest,
) -> str:
    """Return a continuity prompt block when allowed; otherwise empty string."""
    if not should_use_continuity(user, payload):
        return ""
    assert user is not None
    entries = fetch_prior_checkins(db, user)
    return format_continuity_block(entries)
