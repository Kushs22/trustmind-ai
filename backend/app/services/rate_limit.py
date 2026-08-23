"""In-memory sliding-window rate limiter for public API endpoints."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from typing import Literal

from fastapi import Request

from app.config import settings

_lock = Lock()
_buckets: dict[str, deque[float]] = defaultdict(deque)

RateLimitAction = Literal[
    "analyse",
    "auth_login",
    "auth_register",
    "auth_anonymous",
    "chat",
    "upload",
    "transcribe",
]


class RateLimitExceeded(Exception):
    def __init__(self, message: str, *, retry_after_seconds: int | None = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


def client_key(request: Request) -> str:
    """Best-effort client identity for rate limiting (IP behind proxies)."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host or "unknown"
    return "unknown"


def _limits_for(action: RateLimitAction) -> tuple[int, float]:
    # Prefer RATE_LIMIT_WINDOW_SECONDS; honour legacy UPLOAD_RATE_LIMIT_WINDOW_SECONDS.
    window = float(
        settings.rate_limit_window_seconds
        if settings.rate_limit_window_seconds != 60
        else settings.upload_rate_limit_window_seconds
        or settings.rate_limit_window_seconds
    )
    mapping: dict[RateLimitAction, int] = {
        "analyse": settings.analyse_rate_limit_count,
        "auth_login": settings.auth_login_rate_limit_count,
        "auth_register": settings.auth_register_rate_limit_count,
        "auth_anonymous": settings.auth_anonymous_rate_limit_count,
        "chat": settings.chat_rate_limit_count,
        "upload": settings.upload_rate_limit_count,
        "transcribe": settings.transcribe_rate_limit_count,
    }
    return mapping[action], window


def check_rate_limit(
    client_id: str,
    *,
    action: RateLimitAction = "upload",
    limit: int | None = None,
    window_seconds: float | None = None,
) -> None:
    """Raise RateLimitExceeded if the client exceeds the configured window.

    ``client_id`` should already include a stable identity (IP). Prefer
    ``enforce_rate_limit(request, action=...)`` from routers.
    """
    default_limit, default_window = _limits_for(action)
    window = float(window_seconds if window_seconds is not None else default_window)
    max_hits = int(limit if limit is not None else default_limit)
    bucket_key = f"{action}:{client_id}"
    now = time.monotonic()
    with _lock:
        q = _buckets[bucket_key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= max_hits:
            retry_after = max(1, int(window - (now - q[0])) + 1) if q else int(window)
            raise RateLimitExceeded(
                f"Too many requests. Limit is {max_hits} per {int(window)} seconds. "
                "Please wait a moment and try again.",
                retry_after_seconds=retry_after,
            )
        q.append(now)


def enforce_rate_limit(request: Request, *, action: RateLimitAction) -> None:
    """Apply the named rate limit for the request client."""
    check_rate_limit(client_key(request), action=action)
