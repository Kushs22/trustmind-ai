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
        "Never diagnose. Crisis / safety in the CURRENT message always takes priority. "
        "If the latest user message is in another language or asks to switch language, "
        "reply in that language even if earlier assistant turns were English. "
        "Never claim you can only speak English."
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


_LATIN_RE = re.compile(r"[A-Za-z]")
_LETTER_RE = re.compile(r"[^\W\d_]", re.UNICODE)
_LANG_SWITCH_RE = re.compile(
    r"\b("
    r"speak|talk|reply|respond|write|answer|chat|continue"
    r")\b.{0,24}\b("
    r"in|on"
    r")\b.{0,12}\b("
    r"[a-z]{3,}"
    r")\b|"
    r"\b("
    r"en|in|auf|en|em|på|na|nel"
    r")\b\s+("
    r"español|spanish|français|french|deutsch|german|italiano|italian|"
    r"português|portuguese|hindi|हिंदी|हिन्दी|marathi|मराठी|telugu|తెలుగు|"
    r"tamil|தமிழ்|gujarati|ગુજરાતી|punjabi|ਪੰਜਾਬੀ|urdu|اردو|"
    r"arabic|العربية|chinese|中文|japanese|日本語|korean|한국어|"
    r"russian|русский|polish|polski|turkish|türkçe|dutch|nederlands|"
    r"swedish|svenska|greek|ελληνικά|bengali|বাংলা"
    r")\b",
    re.IGNORECASE,
)


def _has_non_latin_letters(text: str) -> bool:
    """True if message contains letters outside basic Latin (e.g. Devanagari, Cyrillic)."""
    for ch in text or "":
        if not _LETTER_RE.match(ch):
            continue
        # Basic Latin + Latin-1 supplement letters still "latin-ish"; treat
        # anything outside ASCII letters as a strong multilingual signal.
        if ord(ch) > 127:
            return True
    return False


def _mostly_non_english_script(text: str) -> bool:
    letters = [ch for ch in (text or "") if _LETTER_RE.match(ch)]
    if not letters:
        return False
    non_ascii = sum(1 for ch in letters if ord(ch) > 127)
    return non_ascii / max(len(letters), 1) >= 0.25


def _requests_language_switch(text: str) -> bool:
    return bool(_LANG_SWITCH_RE.search(text or ""))


def _needs_language_mirror(text: str) -> bool:
    """User is clearly not writing plain English-only, or asked to switch language."""
    raw = (text or "").strip()
    if not raw:
        return False
    if _requests_language_switch(raw):
        return True
    if _mostly_non_english_script(raw):
        return True
    if _has_non_latin_letters(raw):
        return True
    return False


def _claims_english_only(reply: str) -> bool:
    lowered = (reply or "").lower()
    return any(
        phrase in lowered
        for phrase in (
            "only communicate in english",
            "only speak english",
            "can only communicate in english",
            "i can only communicate in english",
            "only available in english",
            "reply in english only",
            "must use english",
            "only respond in english",
            "i'm only able to communicate in english",
            "i am only able to communicate in english",
            "cannot speak other languages",
            "can't speak other languages",
            "don't support other languages",
            "do not support other languages",
        )
    )


def _language_override_block(user_message: str) -> str:
    return (
        "LANGUAGE POLICY (mandatory):\n"
        "- Mirror the language of the LATEST user message exactly "
        "(same language and, when practical, same script).\n"
        "- Examples: Spanish→Spanish, Hindi→Hindi, Telugu→Telugu, French→French, "
        "Arabic→Arabic, Chinese→Chinese, etc.\n"
        "- If the user asks to switch languages, switch immediately.\n"
        "- Earlier English assistant turns do NOT lock the chat to English.\n"
        "- NEVER say you can only communicate in English.\n"
        f"- Latest user message for language choice:\n{user_message}"
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

    if not settings.openai_api_key and not settings.gemini_api_key and not settings.groq_api_key:
        return _fallback_reply(text, safety=safety), safety

    try:
        from app.services.llm_provider import complete_json

        system = (
            "You are TrustMind AI — a warm, careful multilingual wellbeing "
            "check-in companion for students. You continue an existing check-in.\n\n"
            "Hard rules:\n"
            "- You are multilingual. Always reply in the same language as the "
            "user's latest message (any language the model supports).\n"
            "- NEVER say you can only communicate in English, or refuse other languages.\n"
            "- If the user asks to switch language, switch immediately even if "
            "earlier turns were in English.\n"
            "- Speak in warm second person; be empathetic; do NOT diagnose.\n"
            "- Never say \"you have\", \"this proves\", or \"the diagnosis is\".\n"
            "- Keep replies to 2–5 short sentences.\n"
            "- If the latest message suggests suicidal distress or self-harm, "
            "lead with genuine care and urge getting support now.\n"
            "- When soft tone cues are provided for spoken audio, gently "
            "acknowledge how the message may have sounded without clinical claims.\n"
            "- This is not therapy or a clinical service.\n"
            "- Return ONLY valid JSON: "
            '{"reply": "...", "safety_triggered": true|false}'
        )
        latest = (
            f"{audio_prompt_block.strip()}\n\nStored/display message:\n{text}"
            if (audio_prompt_block or "").strip()
            else f"Latest user message:\n{text}"
        )
        lang_block = _language_override_block(text)
        user_prompt = (
            f"{lang_block}\n\n"
            + (f"{thread_block}\n\n" if thread_block else "")
            + latest
        )

        def _once(*, reinforce: bool = False) -> tuple[str, bool]:
            prompt = user_prompt
            if reinforce:
                prompt = (
                    "RETRY REQUIRED: Your previous draft wrongly claimed an English-only "
                    "limit. That is false. Reply in the SAME language as the latest user "
                    "message. Do not mention English-only restrictions.\n\n"
                    + user_prompt
                )
            raw, err, provider = complete_json(
                system=system,
                user=prompt,
                temperature=min(0.7, float(settings.openai_temperature) + 0.15),
                max_tokens=max(64, int(settings.openai_chat_max_tokens)),
                openai_model=settings.openai_chat_model or settings.openai_model,
                gemini_model=settings.gemini_chat_model or settings.gemini_model,
                groq_model=settings.groq_model,
            )
            if err and not raw:
                logger.warning("Follow-up LLM failed (%s): %s", provider or "none", err)
                return _fallback_reply(text, safety=safety), safety
            parsed = json.loads(raw) if raw else {}
            reply = _clip(str(parsed.get("reply") or "").strip())
            flagged = bool(parsed.get("safety_triggered")) or safety
            if not reply:
                reply = _fallback_reply(text, safety=flagged)
            return reply, flagged

        reply, flagged = _once()
        if _claims_english_only(reply) and (
            _needs_language_mirror(text) or _requests_language_switch(text)
        ):
            logger.warning(
                "Follow-up claimed English-only; retrying with multilingual override"
            )
            reply, flagged = _once(reinforce=True)
            if _claims_english_only(reply):
                # Strip the false limitation rather than showing it to the user.
                reply = (
                    "Of course — I can continue in your language. "
                    "Please share what's on your mind, and I'll reply in the same "
                    "language you're using. This is supportive check-in help, not a diagnosis."
                )
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
