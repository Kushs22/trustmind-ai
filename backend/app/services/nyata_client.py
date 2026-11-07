"""Nyata AI live local listings client (additive to TrustMind RAG).

POST https://nyataai.co.uk/external_api.php with X-API-Key.
Do not cache Nyata responses — listings are live.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

NYATA_ENDPOINT = "https://nyataai.co.uk/external_api.php"
NYATA_MODEL = "nyata-1"
BRISTOL_LOCATION = {"latitude": 51.4545, "longitude": -2.5879}
BRISTOL_CITY = "Bristol"
MAX_RETRIES = 4
REQUEST_TIMEOUT_SECONDS = 20

CONCERN_QUERIES: dict[str, str] = {
    "anxiety": "I'm feeling anxious and need local support in Bristol",
    "depression": "I need mental health support or a support group in Bristol",
    "loneliness": "I'm feeling isolated and want to meet people in Bristol",
    "food": "I need help finding free food or a food bank in Bristol",
    "housing": "I need help with housing or emergency shelter in Bristol",
    "employment": "I need employment support in Bristol",
    "mental_health": "I need mental health support in Bristol",
}

_FOOD_HINTS = ("food bank", "foodbank", "hungry", "no food", "can't afford food", "meal")
_HOUSING_HINTS = ("homeless", "evict", "no roof", "sofa surf", "housing", "shelter")
_WORK_HINTS = ("unemployed", "job centre", "lost my job", "can't find work")
_LONELY_HINTS = ("lonely", "loneliness", "isolated", "no friends", "nobody to talk")


def map_concern_to_category(prediction: str | None, user_text: str = "") -> str:
    """Map TrustMind assessment + user wording to a Nyata concern category."""
    blob = (user_text or "").lower()
    if any(h in blob for h in _HOUSING_HINTS):
        return "housing"
    if any(h in blob for h in _FOOD_HINTS):
        return "food"
    if any(h in blob for h in _WORK_HINTS):
        return "employment"
    if any(h in blob for h in _LONELY_HINTS):
        return "loneliness"
    key = (prediction or "").strip().lower()
    if key in {"anxiety"}:
        return "anxiety"
    if key in {"depression"}:
        return "depression"
    if key in {"suicidewatch", "self.suicidewatch"}:
        return "mental_health"
    if key in {"offmychest"}:
        return "loneliness"
    return "mental_health"


def _query_for(category: str, user_message: str) -> str:
    mapped = CONCERN_QUERIES.get(category) or CONCERN_QUERIES["mental_health"]
    extra = (user_message or "").strip()
    if extra and len(extra) < 280:
        return f"{mapped}. The person said: {extra}"
    return mapped


def _parse_quota(payload: dict[str, Any]) -> int | None:
    usage = payload.get("api_usage") or payload.get("nyata", {}).get("api_usage")
    if not isinstance(usage, dict):
        return None
    for key in ("remaining", "requests_remaining", "quota_remaining"):
        if key in usage:
            try:
                return int(usage[key])
            except (TypeError, ValueError):
                return None
    used = usage.get("used") or usage.get("requests_used")
    limit = usage.get("limit") or usage.get("requests_limit")
    try:
        if used is not None and limit is not None:
            return int(limit) - int(used)
    except (TypeError, ValueError):
        return None
    return None


def _empty_result(*, error: str, category: str) -> dict[str, Any]:
    return {
        "ok": False,
        "error": error,
        "category": category,
        "reply": "",
        "results": [],
        "quota_remaining": None,
    }


def get_bristol_support(
    user_message: str,
    category: str = "mental_health",
) -> dict[str, Any]:
    """Fetch live Bristol listings from Nyata. Never raises to the analyse path."""
    category = (category or "mental_health").strip().lower() or "mental_health"
    api_key = (settings.nyata_api_key or "").strip()
    if not api_key:
        return _empty_result(error="not_configured", category=category)
    if not settings.enable_nyata:
        return _empty_result(error="disabled", category=category)

    url = (settings.nyata_api_url or NYATA_ENDPOINT).strip() or NYATA_ENDPOINT
    model = (settings.nyata_model or NYATA_MODEL).strip() or NYATA_MODEL
    body = {
        "model": model,
        "messages": [{"role": "user", "content": _query_for(category, user_message)}],
        "max_tokens": 400,
        "temperature": 0.2,
        "city": BRISTOL_CITY,
        "location": {
            "latitude": settings.nyata_latitude,
            "longitude": settings.nyata_longitude,
        },
    }
    payload_bytes = json.dumps(body).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key,
        "User-Agent": "TrustMind-AI/1.0 (nyata-partnership)",
        "Accept": "application/json",
    }

    last_error = "unknown"
    for attempt in range(MAX_RETRIES + 1):
        req = urllib.request.Request(url, data=payload_bytes, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                status = getattr(resp, "status", 200)
        except urllib.error.HTTPError as exc:
            status = int(exc.code)
            raw = ""
            try:
                raw = exc.read().decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                raw = ""
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            last_error = f"http_{status}"
            if status in {429} or 500 <= status < 600:
                if attempt < MAX_RETRIES:
                    delay = 2**attempt
                    if retry_after:
                        try:
                            delay = min(60, max(1, int(retry_after)))
                        except ValueError:
                            pass
                    logger.warning("Nyata HTTP %s — retry in %ss", status, delay)
                    time.sleep(delay)
                    continue
            if status == 403 and "quota" in raw.lower():
                return _empty_result(error="quota_exceeded", category=category)
            logger.warning("Nyata request failed: HTTP %s", status)
            return _empty_result(error=last_error, category=category)
        except Exception as exc:  # noqa: BLE001
            last_error = f"{type(exc).__name__}"
            if attempt < MAX_RETRIES:
                time.sleep(min(8, 2**attempt))
                continue
            logger.warning("Nyata request failed: %s", last_error)
            return _empty_result(error=last_error, category=category)

        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return _empty_result(error="invalid_json", category=category)

        if status != 200 or not isinstance(payload, dict):
            return _empty_result(error=f"http_{status}", category=category)

        choices = payload.get("choices") or []
        reply = ""
        if choices and isinstance(choices[0], dict):
            message = choices[0].get("message") or {}
            reply = str(message.get("content") or "").strip()
        nyata = payload.get("nyata") if isinstance(payload.get("nyata"), dict) else {}
        results = list(nyata.get("results") or [])
        quota = _parse_quota(payload)
        if quota is not None:
            logger.info("Nyata quota remaining=%s", quota)
        return {
            "ok": True,
            "error": "",
            "category": category,
            "reply": reply,
            "results": results,
            "quota_remaining": quota,
        }

    return _empty_result(error=last_error, category=category)
