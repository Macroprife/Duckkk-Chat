"""Duck Chat — in-memory per-IP rate limiter (token-bucket-ish)."""

import time
from collections import deque
from typing import Optional

from duckapp.config import AUTH_RATE_MAX, AUTH_RATE_WINDOW

_BUCKETS: dict[str, deque[float]] = {}


def check_rate(ip: str | None, max_requests: int | None = None, window_seconds: int | None = None) -> bool:
    """Return True if request is allowed; False to deny (429)."""
    key = ip or "anon"
    max_r = max_requests if max_requests is not None else AUTH_RATE_MAX
    win = window_seconds if window_seconds is not None else AUTH_RATE_WINDOW
    now = time.time()
    bucket = _BUCKETS.setdefault(key, deque())
    cutoff = now - win
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= max_r:
        return False
    bucket.append(now)
    return True
