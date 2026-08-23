"""Multi-provider JSON LLM calls with free-first fallback.

Order in `auto` mode: Groq (free/fast) → Gemini (free) → OpenAI (paid).
No free API is 100% guaranteed (rate limits / model churn), but this chain
keeps TrustMind working when one provider is exhausted.
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
    "rate limit",
    "429",
)

# Tried in order when GEMINI_MODEL is missing/404 (2.0 Flash shut down June 2026).
_GEMINI_MODEL_FALLBACKS = (
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-3-flash-preview",
)


def llm_configured() -> bool:
    return bool(
        settings.groq_api_key or settings.gemini_api_key or settings.openai_api_key
    )


def _is_quota_error(message: str) -> bool:
    lowered = (message or "").lower()
    return any(tok in lowered for tok in _QUOTA_TOKENS)


def keyword_fallback_grounding_status(error: str | None = None) -> str:
    """
    Short grounding_status for DB/UI when the pipeline falls back to keywords.

    Full provider HTTP bodies must stay in logs only — never dump them into
    grounding_status (VARCHAR overflow / noisy UI).
    """
    err_l = (error or "").lower()
    if _is_quota_error(err_l):
        return "keyword_fallback (provider_quota)"
    if any(
        tok in err_l
        for tok in ("404", "does not exist", "not found", "model_not_found")
    ):
        return "keyword_fallback (model_unavailable)"
    if any(tok in err_l for tok in ("timeout", "timed out", "deadline")):
        return "keyword_fallback (timeout)"
    if any(tok in err_l for tok in ("401", "403", "invalid api key", "authentication")):
        return "keyword_fallback (auth_error)"
    return "keyword_fallback (provider_error)"


def _provider_order() -> list[str]:
    """Prefer free/reliable providers first in auto mode."""
    mode = (settings.llm_provider or "auto").strip().lower()
    if mode in {"groq", "gemini", "openai"}:
        return [mode]
    if mode == "free":
        order: list[str] = []
        if settings.groq_api_key:
            order.append("groq")
        if settings.gemini_api_key:
            order.append("gemini")
        return order
    # auto: free first, then paid OpenAI
    order = []
    if settings.groq_api_key:
        order.append("groq")
    if settings.gemini_api_key:
        order.append("gemini")
    if settings.openai_api_key:
        order.append("openai")
    return order


def _call_openai_compatible_json(
    *,
    api_key: str,
    base_url: str,
    model_name: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int | None,
) -> tuple[str, str]:
    try:
        from openai import OpenAI
    except Exception as exc:  # noqa: BLE001
        return "", f"openai_import: {type(exc).__name__}: {exc}"

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=float(settings.openai_chat_timeout_seconds),
    )
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
    model_name = (model or settings.openai_model or "gpt-4.1").strip()
    return _call_openai_compatible_json(
        api_key=settings.openai_api_key,
        base_url="https://api.openai.com/v1",
        model_name=model_name,
        system=system,
        user=user,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _call_groq_json(
    *,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int | None,
    model: str | None,
) -> tuple[str, str]:
    if not settings.groq_api_key:
        return "", "GROQ_API_KEY missing"
    model_name = (model or settings.groq_model or "openai/gpt-oss-120b").strip()
    return _call_openai_compatible_json(
        api_key=settings.groq_api_key,
        base_url=(settings.groq_base_url or "https://api.groq.com/openai/v1").rstrip("/"),
        model_name=model_name,
        system=system,
        user=user,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _call_gemini_json_once(
    *,
    model_name: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int | None,
) -> tuple[str, str]:
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

    preferred = (model or settings.gemini_model or "gemini-2.5-flash").strip()
    candidates: list[str] = []
    for name in (preferred, *_GEMINI_MODEL_FALLBACKS):
        if name and name not in candidates:
            candidates.append(name)

    errors: list[str] = []
    for model_name in candidates:
        text, err = _call_gemini_json_once(
            model_name=model_name,
            system=system,
            user=user,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if text and not err:
            if model_name != preferred:
                logger.info("Gemini fallback model succeeded: %s", model_name)
            return text, ""
        if err:
            errors.append(f"{model_name}: {err}")
            if "404" not in err and "not found" not in err.lower():
                return "", err
    return "", " | ".join(errors) or "gemini_failure"


def complete_json(
    *,
    system: str,
    user: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
    openai_model: str | None = None,
    gemini_model: str | None = None,
    groq_model: str | None = None,
) -> tuple[str, str, str]:
    """
    Return (response_text, error, provider_used).

    provider_used is 'groq', 'gemini', 'openai', or '' on total failure.
    """
    temp = (
        float(settings.openai_temperature)
        if temperature is None
        else float(temperature)
    )
    order = _provider_order()
    if not order:
        return (
            "",
            "No LLM provider configured (set GROQ_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY)",
            "",
        )

    errors: list[str] = []
    for provider in order:
        if provider == "groq":
            text, err = _call_groq_json(
                system=system,
                user=user,
                temperature=temp,
                max_tokens=max_tokens,
                model=groq_model,
            )
            if text and not err:
                return text, "", "groq"
            if err:
                errors.append(f"groq: {err}")
                logger.warning("Groq JSON call failed: %s", err)
                continue
        elif provider == "openai":
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
                continue

    return "", " | ".join(errors) or "llm_failure", ""
