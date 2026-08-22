"""Multi-turn wellbeing chat continuation for saved (and ephemeral) check-ins.

Follow-ups are warm, non-diagnostic reflections — not a new clinical assessment.
Crisis language still surfaces support resources. Conversation history for a
saved check-in is loaded server-side; clients never supply authoritative history
when a check_in_id is present.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.config import settings
from app.models import CheckIn, User
from app.services.support_resources import get_support_resources

logger = logging.getLogger(__name__)

ChatRole = Literal["user", "assistant"]

MAX_THREAD_MESSAGES = 40
# Keep chat prompts short so follow-ups stay snappy.
MAX_PROMPT_MESSAGES = 12
MAX_MESSAGE_CHARS = 4000
_CRISIS_PATTERNS = (
    r"\bsuicid",
    r"\bkill myself\b",
    r"\bend my life\b",
    r"\bwant to die\b",
    r"\bself[-\s]?harm\b",
    r"\bhurt myself\b",
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _clip(text: str, max_len: int = MAX_MESSAGE_CHARS) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3] + "..."


def make_message(role: ChatRole, content: str, **extra: Any) -> dict[str, Any]:
    msg: dict[str, Any] = {
        "role": role,
        "content": _clip(content),
        "created_at": _now_iso(),
    }
    msg.update({k: v for k, v in extra.items() if v is not None})
    return msg


def parse_conversation_json(raw: str | None) -> list[dict[str, Any]]:
    if not raw or not str(raw).strip():
        return []
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(parsed, list):
        return []
    out: list[dict[str, Any]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str):
            continue
        content = content.strip()
        if not content:
            continue
        entry: dict[str, Any] = {
            "role": role,
            "content": _clip(content),
            "created_at": item.get("created_at") or _now_iso(),
        }
        if item.get("safety_triggered"):
            entry["safety_triggered"] = True
        if item.get("input_type") in ("text", "audio"):
            entry["input_type"] = item["input_type"]
        if isinstance(item.get("transcript"), str) and item["transcript"].strip():
            entry["transcript"] = _clip(item["transcript"], 2000)
        if isinstance(item.get("tone_summary"), str) and item["tone_summary"].strip():
            entry["tone_summary"] = _clip(item["tone_summary"], 400)
        if isinstance(item.get("affect_cues"), list):
            entry["affect_cues"] = [
                str(c).strip() for c in item["affect_cues"] if str(c).strip()
            ][:6]
        out.append(entry)
    return out[-MAX_THREAD_MESSAGES:]


def dump_conversation(messages: list[dict[str, Any]]) -> str:
    return json.dumps(messages[-MAX_THREAD_MESSAGES:], ensure_ascii=False)


def seed_conversation_from_check_in(
    *,
    user_text: str | None,
    assistant_text: str | None,
    is_private: bool,
) -> list[dict[str, Any]]:
    """Build the opening user + assistant turn for a newly saved check-in."""
    messages: list[dict[str, Any]] = []
    preview = None if is_private else _clip(user_text or "", 500)
    if preview:
        messages.append(make_message("user", preview))
    reflection = _clip(assistant_text or "", MAX_MESSAGE_CHARS)
    if reflection:
        messages.append(make_message("assistant", reflection))
    return messages


def messages_for_row(row: CheckIn) -> list[dict[str, Any]]:
    """Return stored thread, or synthesise one from preview + reflection."""
    stored = parse_conversation_json(getattr(row, "conversation_json", None))
    if stored:
        return stored
    return seed_conversation_from_check_in(
        user_text=row.text_preview,
        assistant_text=row.explanation,
        is_private=bool(row.is_private),
    )


def format_thread_for_prompt(messages: list[dict[str, Any]]) -> str:
    if not messages:
        return ""
    lines = ["Conversation so far (for continuity — not a diagnosis record):"]
    for msg in messages[-MAX_PROMPT_MESSAGES:]:
        label = "User" if msg.get("role") == "user" else "TrustMind"
        content = _clip(str(msg.get("content") or ""), 900)
        lines.append(f"{label}: {content}")
    lines.append(
        "Continuity rules: Acknowledge earlier turns briefly when helpful. "
        "Prioritise the latest user message. Do not invent history. "
        "Never diagnose. Crisis / safety in the CURRENT message always takes priority."
    )
    return "\n".join(lines)


def _looks_like_crisis(text: str) -> bool:
    lowered = (text or "").lower()
    return any(re.search(pat, lowered) for pat in _CRISIS_PATTERNS)


def _fallback_reply(user_message: str, *, safety: bool) -> str:
    if safety:
        return (
            "I'm really sorry you're feeling this way. You're not alone, and "
            "reaching out matters. TrustMind AI can't provide crisis counselling — "
            "please use the urgent support options below, or call 999 if you are "
            "in immediate danger."
        )
    snippet = _clip(user_message, 80)
    if snippet:
        return (
            f"Thanks for sharing more — it sounds like \"{snippet}\" is still on "
            "your mind. I'm here to listen without judging. If it helps, try one "
            "small supportive step today, and remember this is wellbeing support "
            "information, not a diagnosis."
        )
    return (
        "Thanks for checking in again. I'm here to listen. Share whatever feels "
        "comfortable — this is wellbeing support information, not a diagnosis."
    )


def generate_follow_up_reply(
    *,
    user_message: str,
    prior_messages: list[dict[str, Any]],
    audio_prompt_block: str | None = None,
) -> tuple[str, bool]:
    """
    Generate a warm follow-up reflection.

    When audio_prompt_block is set, the model also receives soft tone cues
    (how the speech may have sounded) — never as a clinical emotion label.

    Returns (reply_text, safety_triggered).
    """
    text = _clip(user_message)
    if not text:
        raise ValueError("Message cannot be empty.")

    safety = _looks_like_crisis(text)
    if audio_prompt_block:
        safety = safety or _looks_like_crisis(audio_prompt_block)
    thread_block = format_thread_for_prompt(prior_messages)

    if not settings.openai_api_key:
        return _fallback_reply(text, safety=safety), safety

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        system = (
            "You are TrustMind AI — a warm, careful wellbeing check-in companion "
            "for students. You continue an existing check-in conversation.\n\n"
            "Rules:\n"
            "- Speak in warm second person.\n"
            "- Be empathetic and validating; do NOT diagnose.\n"
            "- Never say \"you have\", \"this proves\", or \"the diagnosis is\".\n"
            "- Keep replies to 2–5 short sentences.\n"
            "- If the latest message suggests suicidal distress or self-harm, "
            "lead with genuine care and urge getting support now.\n"
            "- When soft tone cues are provided for spoken audio, gently "
            "acknowledge how the message may have sounded (e.g. tired, strained, "
            "calmer) without claiming clinical emotion detection accuracy.\n"
            "- Prefer \"it sounded like…\" / \"from how that came across…\" "
            "over \"your mood is…\" or \"we detected…\".\n"
            "- This is not therapy or a clinical service.\n"
            "- Return ONLY valid JSON: "
            '{"reply": "...", "safety_triggered": true|false}'
        )
        latest = (
            f"{audio_prompt_block.strip()}\n\nStored/display message:\n{text}"
            if (audio_prompt_block or "").strip()
            else f"Latest user message:\n{text}"
        )
        user_prompt = (f"{thread_block}\n\n" if thread_block else "") + latest

        chat_model = (settings.openai_chat_model or settings.openai_model).strip()
        response = client.chat.completions.create(
            model=chat_model,
            temperature=min(0.7, float(settings.openai_temperature) + 0.15),
            max_tokens=max(64, int(settings.openai_chat_max_tokens)),
            timeout=float(settings.openai_chat_timeout_seconds),
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
        )
        raw = (response.choices[0].message.content or "").strip()
        parsed = json.loads(raw) if raw else {}
        reply = _clip(str(parsed.get("reply") or "").strip())
        flagged = bool(parsed.get("safety_triggered")) or safety
        if not reply:
            reply = _fallback_reply(text, safety=flagged)
        return reply, flagged
    except Exception:
        logger.exception("Follow-up LLM reply failed; using fallback")
        return _fallback_reply(text, safety=safety), safety


def append_follow_up_to_check_in(
    db: Session,
    user: User,
    check_in_id: str,
    message: str,
    *,
    audio_meta: dict[str, Any] | None = None,
) -> tuple[CheckIn, dict[str, Any], list[dict[str, Any]]]:
    """
    Persist a user follow-up + assistant reply on an owned check-in.

    audio_meta may include transcript, tone_summary, affect_cues, prompt_block.

    Returns (row, assistant_message, full_messages).
    """
    row = (
        db.query(CheckIn)
        .filter(CheckIn.id == check_in_id, CheckIn.user_id == user.id)
        .first()
    )
    if row is None:
        raise LookupError("Check-in not found")

    if row.is_private:
        raise PermissionError(
            "This check-in was analysed privately, so the chat thread cannot continue."
        )

    prior = messages_for_row(row)
    meta = audio_meta or {}
    user_extra: dict[str, Any] = {}
    if meta.get("input_type") == "audio":
        user_extra["input_type"] = "audio"
        if meta.get("transcript"):
            user_extra["transcript"] = _clip(str(meta["transcript"]), 2000)
        if meta.get("tone_summary"):
            user_extra["tone_summary"] = _clip(str(meta["tone_summary"]), 400)
        if isinstance(meta.get("affect_cues"), list):
            user_extra["affect_cues"] = [
                str(c).strip() for c in meta["affect_cues"] if str(c).strip()
            ][:6]
    user_msg = make_message("user", message, **user_extra)
    reply_text, safety = generate_follow_up_reply(
        user_message=message,
        prior_messages=prior,
        audio_prompt_block=meta.get("prompt_block"),
    )
    assistant_msg = make_message(
        "assistant",
        reply_text,
        safety_triggered=safety or None,
    )
    updated = prior + [user_msg, assistant_msg]
    row.conversation_json = dump_conversation(updated)
    # Keep the detail-page reflection aligned with the latest assistant turn.
    row.explanation = reply_text
    try:
        db.commit()
        db.refresh(row)
    except Exception:
        db.rollback()
        logger.exception(
            "Failed to append chat message for check_in=%s user=%s",
            check_in_id,
            user.id,
        )
        raise
    return row, assistant_msg, updated


def support_payload_if_needed(safety_triggered: bool) -> list[dict[str, str]]:
    if not safety_triggered:
        return []
    return get_support_resources(force=True)
