"""Ephemeral and saved chat follow-up endpoint."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_optional
from app.models import User
from app.schemas.analyse import SupportResourceOut
from app.schemas.check_in import (
    ChatFollowUpRequest,
    ChatFollowUpResponse,
    ChatMessageOut,
)
from app.services.audio_tone_service import process_chat_audio
from app.services.conversation_service import (
    append_follow_up_to_check_in,
    generate_follow_up_reply,
    make_message,
    support_payload_if_needed,
)
from app.services.file_validation_service import FileValidationError
from app.services.rate_limit import RateLimitExceeded, enforce_rate_limit
from app.services.transcription_service import TranscriptionError

router = APIRouter(tags=["chat"])


def _to_message_out(msg: dict) -> ChatMessageOut:
    return ChatMessageOut(
        role=msg["role"],
        content=msg["content"],
        created_at=msg.get("created_at"),
        safety_triggered=bool(msg.get("safety_triggered")),
        input_type=msg.get("input_type"),
        transcript=msg.get("transcript"),
        tone_summary=msg.get("tone_summary"),
        affect_cues=list(msg.get("affect_cues") or []),
    )


def _rate_limit_or_raise(request: Request) -> None:
    try:
        enforce_rate_limit(request, action="chat")
    except RateLimitExceeded as exc:
        headers = {}
        if exc.retry_after_seconds is not None:
            headers["Retry-After"] = str(exc.retry_after_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers=headers or None,
        ) from exc


def _parse_history_json(raw: str | None) -> list[dict[str, Any]]:
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
        if not content.strip():
            continue
        entry: dict[str, Any] = {
            "role": role,
            "content": content.strip(),
            "created_at": item.get("created_at"),
            "safety_triggered": bool(item.get("safety_triggered")),
        }
        if item.get("input_type") in ("text", "audio"):
            entry["input_type"] = item["input_type"]
        if isinstance(item.get("transcript"), str):
            entry["transcript"] = item["transcript"]
        if isinstance(item.get("tone_summary"), str):
            entry["tone_summary"] = item["tone_summary"]
        if isinstance(item.get("affect_cues"), list):
            entry["affect_cues"] = [
                str(c).strip() for c in item["affect_cues"] if str(c).strip()
            ][:6]
        out.append(entry)
    return out


def _audio_meta_from_processed(processed: dict[str, Any]) -> dict[str, Any]:
    return {
        "input_type": "audio",
        "transcript": processed.get("transcript"),
        "tone_summary": processed.get("tone_summary"),
        "affect_cues": list(processed.get("affect_cues") or []),
        "prompt_block": processed.get("prompt_block"),
    }


@router.post(
    "/api/v1/chat/follow-up",
    response_model=ChatFollowUpResponse,
    summary="Continue a wellbeing chat thread",
    description=(
        "Append a follow-up message. When `check_in_id` is set, the thread is "
        "loaded and persisted server-side (auth required). Otherwise `history` "
        "is used as ephemeral prompt context only."
    ),
)
def chat_follow_up(
    payload: ChatFollowUpRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
) -> ChatFollowUpResponse:
    _rate_limit_or_raise(request)
    message = (payload.message or "").strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message cannot be empty.",
        )

    check_in_id = (payload.check_in_id or "").strip() or None
    if check_in_id:
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sign in to continue a saved check-in chat.",
            )
        try:
            _row, assistant_msg, messages = append_follow_up_to_check_in(
                db, user, check_in_id, message
            )
        except LookupError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        except PermissionError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        safety = bool(assistant_msg.get("safety_triggered"))
        return ChatFollowUpResponse(
            check_in_id=check_in_id,
            reply=assistant_msg["content"],
            safety_triggered=safety,
            support_resources=[
                SupportResourceOut(**r) for r in support_payload_if_needed(safety)
            ],
            messages=[_to_message_out(m) for m in messages],
            persisted=True,
        )

    prior = [
        {
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at,
            "safety_triggered": m.safety_triggered,
            "input_type": m.input_type,
            "transcript": m.transcript,
            "tone_summary": m.tone_summary,
            "affect_cues": list(m.affect_cues or []),
        }
        for m in (payload.history or [])
        if m.role in ("user", "assistant") and (m.content or "").strip()
    ]
    reply_text, safety = generate_follow_up_reply(
        user_message=message,
        prior_messages=prior,
    )
    user_msg = make_message("user", message, input_type="text")
    assistant_msg = make_message(
        "assistant",
        reply_text,
        safety_triggered=safety or None,
    )
    messages = prior + [user_msg, assistant_msg]
    return ChatFollowUpResponse(
        check_in_id=None,
        reply=reply_text,
        safety_triggered=safety,
        support_resources=[
            SupportResourceOut(**r) for r in support_payload_if_needed(safety)
        ],
        messages=[_to_message_out(m) for m in messages],
        persisted=False,
    )


@router.post(
    "/api/v1/chat/follow-up-audio",
    response_model=ChatFollowUpResponse,
    summary="Continue chat with spoken audio (transcript + tone cues)",
    description=(
        "Upload a short audio clip. The server transcribes speech (the note), "
        "infers soft non-diagnostic tone cues (how it sounded), and continues "
        "the check-in thread. Original audio is not retained."
    ),
)
async def chat_follow_up_audio(
    request: Request,
    file: UploadFile = File(..., description="Audio clip (webm/mp4/mpeg/wav/ogg)"),
    check_in_id: str | None = Form(default=None),
    history: str | None = Form(
        default=None,
        description="JSON array of prior messages when check_in_id is absent",
    ),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
) -> ChatFollowUpResponse:
    _rate_limit_or_raise(request)

    data = await file.read()
    try:
        processed = process_chat_audio(
            data=data,
            filename=file.filename,
            content_type=file.content_type,
        )
    except FileValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except TranscriptionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    finally:
        await file.close()

    message = processed["content"]
    audio_meta = _audio_meta_from_processed(processed)
    cid = (check_in_id or "").strip() or None
    tone_disclaimer = processed.get("tone_disclaimer")

    if cid:
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sign in to continue a saved check-in chat.",
            )
        try:
            _row, assistant_msg, messages = append_follow_up_to_check_in(
                db,
                user,
                cid,
                message,
                audio_meta=audio_meta,
            )
        except LookupError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        except PermissionError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        safety = bool(assistant_msg.get("safety_triggered"))
        return ChatFollowUpResponse(
            check_in_id=cid,
            reply=assistant_msg["content"],
            safety_triggered=safety,
            support_resources=[
                SupportResourceOut(**r) for r in support_payload_if_needed(safety)
            ],
            messages=[_to_message_out(m) for m in messages],
            persisted=True,
            tone_disclaimer=tone_disclaimer,
        )

    prior = _parse_history_json(history)
    reply_text, safety = generate_follow_up_reply(
        user_message=message,
        prior_messages=prior,
        audio_prompt_block=processed.get("prompt_block"),
    )
    if processed.get("safety_hint"):
        safety = True
    user_msg = make_message(
        "user",
        message,
        input_type="audio",
        transcript=processed.get("transcript"),
        tone_summary=processed.get("tone_summary"),
        affect_cues=list(processed.get("affect_cues") or []),
    )
    assistant_msg = make_message(
        "assistant",
        reply_text,
        safety_triggered=safety or None,
    )
    messages = prior + [user_msg, assistant_msg]
    return ChatFollowUpResponse(
        check_in_id=None,
        reply=reply_text,
        safety_triggered=safety,
        support_resources=[
            SupportResourceOut(**r) for r in support_payload_if_needed(safety)
        ],
        messages=[_to_message_out(m) for m in messages],
        persisted=False,
        tone_disclaimer=tone_disclaimer,
    )
