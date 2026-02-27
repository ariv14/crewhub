"""In-memory sliding window rate limiter.

No external dependencies (no Redis). Each process maintains its own state,
which is fine for single-instance or low-instance deployments (Cloud Run 0-3).
"""

import time
from collections import defaultdict

from fastapi import Depends

from src.config import settings
from src.core.auth import get_current_user_id
from src.core.exceptions import RateLimitError


class RateLimiter:
    """Sliding window rate limiter using in-memory sorted timestamps."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self.window_seconds

        # Prune old entries
        timestamps = self._requests[key]
        self._requests[key] = [t for t in timestamps if t > window_start]

        if len(self._requests[key]) >= self.max_requests:
            return False

        self._requests[key].append(now)
        return True

    def get_limit_info(self, key: str) -> dict:
        now = time.monotonic()
        window_start = now - self.window_seconds
        timestamps = self._requests.get(key, [])
        current = sum(1 for t in timestamps if t > window_start)
        remaining = max(0, self.max_requests - current)
        return {"remaining": remaining, "reset_in_seconds": self.window_seconds}


# Module-level singleton
_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter(
            max_requests=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )
    return _limiter


async def rate_limit_dependency(
    user_id=Depends(get_current_user_id),
) -> None:
    limiter = get_rate_limiter()
    allowed = limiter.check(str(user_id))
    if not allowed:
        info = limiter.get_limit_info(str(user_id))
        raise RateLimitError(
            detail=f"Rate limit exceeded. Try again in {info['reset_in_seconds']} seconds"
        )
