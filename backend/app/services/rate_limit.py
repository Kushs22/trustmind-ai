"""In-memory sliding-window rate limiter for upload endpoints."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from app.config import settings

_lock = Lock()
_buckets: dict[str, deque[float]] = defaultdict(deque)


class RateLimitExceeded(Exception):
    pass


def check_rate_limit(client_key: str) -> None:
    """Raise RateLimitExceeded if the client exceeds the configured window."""
    now = time.monotonic()
    window = float(settings.upload_rate_limit_window_seconds)
    limit = int(settings.upload_rate_limit_count)
    with _lock:
        q = _buckets[client_key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            raise RateLimitExceeded(
                f"Too many upload requests. Limit is {limit} per {int(window)} seconds."
            )
        q.append(now)
