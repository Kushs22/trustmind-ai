"""Chat audio: speech transcript (note) + soft tone cues (how it sounded).

Tone cues are non-diagnostic wellbeing signals for conversation continuity —
never clinical emotion detection or a mood diagnosis.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import settings
from app.services.transcription_service import TranscriptionError, transcribe_audio_bytes

logger = logging.getLogger(__name__)

TONE_DISCLAIMER = (
    "Tone cues are soft impressions of how the message came across — "
    "not a clinical reading of your mood or emotions."
)

_TONE_SYSTEM = """You help TrustMind AI note soft tone cues from a spoken wellbeing check-in.

You receive a speech transcript (what was said) and optional duration.
Infer only gentle, non-clinical cues about how the message may have come across
(e.g. calm, strained, tired-sounding wording, hurried, subdued, brighter).

Strict rules:
- Do NOT diagnose mood, affect disorders, or mental health conditions.
- Do NOT claim certainty ("you are depressed", "this proves anxiety").
- Prefer tentative language: "may have sounded…", "comes across as…".
- If the transcript is too short or unclear, say tone is uncertain.
- Crisis / self-harm language in the transcript must be flagged in safety_hint.

Return ONLY valid JSON:
{
  "tone_summary": "one short sentence on how this may have sounded",
  "affect_cues": ["2-4 short phrases"],
  "uncertainty": "low" | "medium" | "high",
  "safety_hint": false
}
"""


def _fallback_tone(transcript: str, duration_seconds: float | None) -> dict[str, Any]:
    words = len((transcript or "").split())
    uncertainty = "high" if words < 4 else "medium"
    pace_note = ""
    if duration_seconds and words:
        wps = words / max(float(duration_seconds), 0.5)
        if wps < 1.2:
            pace_note = "slower pacing"
        elif wps > 2.8:
            pace_note = "quicker pacing"
    cues = [c for c in [pace_note, "spoken check-in"] if c]
    summary = (
        "Soft tone cues are limited from this clip; we'll rely mainly on what was said."
        if uncertainty == "high"
        else "Spoken check-in — tone cues are approximate from how the words came across."
    )
    return {
        "tone_summary": summary,
        "affect_cues": cues or ["spoken check-in"],
        "uncertainty": uncertainty,
        "safety_hint": False,
    }


def infer_tone_cues(
    *,
    transcript: str,
    duration_seconds: float | None = None,
) -> dict[str, Any]:
    """Infer soft tone cues from transcript (+ duration). Never diagnostic."""
    text = (transcript or "").strip()
    if not text:
        return {
            "tone_summary": "No clear speech to judge tone from.",
            "affect_cues": [],
            "uncertainty": "high",
            "safety_hint": False,
        }

    if not settings.openai_api_key:
        return _fallback_tone(text, duration_seconds)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        duration_line = (
            f"Approx. duration: {duration_seconds:.1f}s\n"
            if duration_seconds is not None
            else ""
        )
        user_prompt = (
            f"{duration_line}"
            f"Speech transcript:\n{text}\n\n"
            "Note soft tone cues only (how this may have sounded). "
            "Not a diagnosis."
        )
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=min(0.5, float(settings.openai_temperature)),
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _TONE_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
        )
        raw = (response.choices[0].message.content or "").strip()
        parsed = json.loads(raw) if raw else {}
        tone_summary = str(parsed.get("tone_summary") or "").strip()
        cues_raw = parsed.get("affect_cues") or []
        affect_cues = [
            str(c).strip() for c in cues_raw if str(c).strip()
        ][:6]
        uncertainty = str(parsed.get("uncertainty") or "medium").strip().lower()
        if uncertainty not in ("low", "medium", "high"):
            uncertainty = "medium"
        if not tone_summary:
            return _fallback_tone(text, duration_seconds)
        return {
            "tone_summary": tone_summary[:400],
            "affect_cues": affect_cues,
            "uncertainty": uncertainty,
            "safety_hint": bool(parsed.get("safety_hint")),
        }
    except Exception:
        logger.exception("Tone cue inference failed; using fallback")
        return _fallback_tone(text, duration_seconds)


def format_audio_user_content(
    *,
    transcript: str,
    tone_summary: str,
    affect_cues: list[str] | None = None,
) -> str:
    """User-facing + stored message body for an audio turn."""
    lines = ["Audio message"]
    note = (transcript or "").strip()
    if note:
        lines.append(f'"{note}"')
    tone = (tone_summary or "").strip()
    if tone:
        lines.append(f"How this sounded: {tone}")
    cues = [c for c in (affect_cues or []) if c]
    if cues:
        lines.append(f"Tone cues: {', '.join(cues)}")
    return "\n".join(lines)


def format_audio_prompt_block(
    *,
    transcript: str,
    tone_summary: str,
    affect_cues: list[str] | None = None,
    uncertainty: str | None = None,
) -> str:
    """Extra context for the follow-up LLM (ethics-aware framing)."""
    cues = [c for c in (affect_cues or []) if c]
    parts = [
        "Latest user turn was spoken audio (not typed).",
        f"Speech content (note): {(transcript or '').strip() or '(empty)'}",
        f"Tone cues (how this sounded — not a clinical mood reading): "
        f"{(tone_summary or '').strip() or '(uncertain)'}",
    ]
    if cues:
        parts.append(f"Soft affect cues: {', '.join(cues)}")
    if uncertainty:
        parts.append(f"Tone-cue uncertainty: {uncertainty}")
    parts.append(
        "Acknowledge both what was said and how it may have sounded, "
        "tentatively and without diagnosing. Prefer phrases like "
        "\"it sounded like…\" / \"from how that came across…\"."
    )
    return "\n".join(parts)


def process_chat_audio(
    *,
    data: bytes,
    filename: str | None,
    content_type: str | None,
) -> dict[str, Any]:
    """
    Transcribe chat audio and infer soft tone cues.

    Temporary audio is deleted by the transcription path; nothing is retained.
    """
    try:
        transcription = transcribe_audio_bytes(
            data=data,
            filename=filename,
            content_type=content_type,
        )
    except TranscriptionError:
        raise

    transcript = (transcription.get("transcript") or "").strip()
    duration = transcription.get("duration_seconds")
    warnings = list(transcription.get("warnings") or [])

    if not transcript:
        raise TranscriptionError(
            "Could not understand the audio. Please try again or type your message."
        )

    tone = infer_tone_cues(transcript=transcript, duration_seconds=duration)
    content = format_audio_user_content(
        transcript=transcript,
        tone_summary=tone["tone_summary"],
        affect_cues=tone.get("affect_cues"),
    )
    prompt_block = format_audio_prompt_block(
        transcript=transcript,
        tone_summary=tone["tone_summary"],
        affect_cues=tone.get("affect_cues"),
        uncertainty=tone.get("uncertainty"),
    )

    return {
        "transcript": transcript,
        "language": transcription.get("language") or "en",
        "duration_seconds": duration,
        "tone_summary": tone["tone_summary"],
        "affect_cues": list(tone.get("affect_cues") or []),
        "tone_uncertainty": tone.get("uncertainty") or "medium",
        "tone_disclaimer": TONE_DISCLAIMER,
        "content": content,
        "prompt_block": prompt_block,
        "safety_hint": bool(tone.get("safety_hint")),
        "warnings": warnings,
    }
