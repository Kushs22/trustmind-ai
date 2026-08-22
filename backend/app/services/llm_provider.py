"""Multi-provider JSON LLM calls: OpenAI primary, Gemini free-tier fallback.

Used when OpenAI credits are exhausted so analyse + chat can keep working
with a Google AI Studio (Gemini) API key.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_QUOTA_TOKENS = (
    "insufficient_quota",
    "credit_balance",
    "exceeded your current quota",
    "billing",
    "rate_limit_exceeded",
)


def llm_configured() -> bool:
    return bool(settings.openai_api_key or settings.gemini_api_key)


def _is_quota_error(message: str) -> bool:
    lowered = (message or "").lower()
    return any(tok in lowered for tok in _QUOTA_TOKENS)


def _provider_order() -> list[str]:
    mode = (settings.llm_provider or "auto").strip().lower()
    if mode == "gemini":
        return ["gemini"]
    if mode == "openai":
        return ["openai"]
    # auto: prefer OpenAI when keyed, else Gemini; on OpenAI failure try Gemini
    order: list[str] = []
    if settings.openai_api_key:
        order.append("openai")
    if settings.gemini_api_key:
        order.append("gemini")
    return order


def _call_openai_json(
    *,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int | None,
    model: str | None,
) -> tuple[str, str]:
    if not settings.openai_api_key:
        return "", "OPENAI_API_KEY missing"
    try:
        from openai import OpenAI
    except Exception as exc:  # noqa: BLE001
        return "", f"openai_import: {type(exc).__name__}: {exc}"

    client = OpenAI(
        api_key=settings.openai_api_key,
        timeout=float(settings.openai_chat_timeout_seconds),
    )
    model_name = (model or settings.openai_model or "gpt-4.1").strip()
    kwargs: dict[str, Any] = {
        "model": model_name,
        "temperature": float(temperature),
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max(32, int(max_tokens))

    try:
        response = client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        if content is None or not str(content).strip():
            return "", "empty_response"
        return str(content).strip(), ""
    except Exception as exc:  # noqa: BLE001
        return "", f"{type(exc).__name__}: {exc}"


def _call_gemini_json(
    *,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int | None,
    model: str | None,
) -> tuple[str, str]:
    if not settings.gemini_api_key:
        return "", "GEMINI_API_KEY missing"

    model_name = (model or settings.gemini_model or "gemini-2.0-flash").strip()
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_name}:generateContent?key={settings.gemini_api_key}"
    )
    generation: dict[str, Any] = {
        "temperature": float(temperature),
        "responseMimeType": "application/json",
    }
    if max_tokens is not None:
        generation["maxOutputTokens"] = max(32, int(max_tokens))

    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": generation,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    timeout = float(settings.openai_chat_timeout_seconds)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        return "", f"HTTPError: {exc.code} {detail}"
    except Exception as exc:  # noqa: BLE001
        return "", f"{type(exc).__name__}: {exc}"

    try:
        parts = body["candidates"][0]["content"]["parts"]
        text = "".join(str(p.get("text") or "") for p in parts).strip()
    except (KeyError, IndexError, TypeError):
        return "", f"gemini_bad_response: {json.dumps(body)[:300]}"
    if not text:
        return "", "empty_response"
    return text, ""


def complete_json(
    *,
    system: str,
    user: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
    openai_model: str | None = None,
    gemini_model: str | None = None,
) -> tuple[str, str, str]:
    """
    Return (response_text, error, provider_used).

    provider_used is 'openai', 'gemini', or '' on total failure.
    """
    temp = (
        float(settings.openai_temperature)
        if temperature is None
        else float(temperature)
    )
    order = _provider_order()
    if not order:
        return "", "No LLM provider configured (set OPENAI_API_KEY or GEMINI_API_KEY)", ""

    errors: list[str] = []
    for provider in order:
        if provider == "openai":
            text, err = _call_openai_json(
                system=system,
                user=user,
                temperature=temp,
                max_tokens=max_tokens,
                model=openai_model,
            )
            if text and not err:
                return text, "", "openai"
            if err:
                errors.append(f"openai: {err}")
                logger.warning("OpenAI JSON call failed: %s", err)
                # On quota, continue to Gemini if available; otherwise stop early
                if _is_quota_error(err) and "gemini" in order:
                    continue
                if "gemini" not in order:
                    return "", err, ""
                continue
        elif provider == "gemini":
            text, err = _call_gemini_json(
                system=system,
                user=user,
                temperature=temp,
                max_tokens=max_tokens,
                model=gemini_model,
            )
            if text and not err:
                return text, "", "gemini"
            if err:
                errors.append(f"gemini: {err}")
                logger.warning("Gemini JSON call failed: %s", err)

    return "", " | ".join(errors) or "llm_failure", ""
