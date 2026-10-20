"""
Utils rate limiter — sliding-window, in-memory throttling.
"""
import asyncio
import time
from collections import deque
from typing import Dict


class RateLimiter:
    """Simple async sliding-window rate limiter keyed by arbitrary strings."""

    def __init__(self):
        self._windows: Dict[str, deque] = {}
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        """Return (allowed, retry_after_seconds)."""
        now = time.monotonic()
        async with self._lock:
            dq = self._windows.setdefault(key, deque())
            while dq and dq[0] < now - window_seconds:
                dq.popleft()
            if len(dq) < limit:
                dq.append(now)
                return True, 0
            oldest = dq[0]
            retry_after = int(oldest + window_seconds - now) + 1
            return False, max(1, retry_after)


utils_rate_limiter = RateLimiter()
