"""3-layer rate limiting for the gateway."""
import time
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class RateLimiter:
    """In-memory sliding window rate limiter. Best-effort — clears on restart."""

    def __init__(self):
        self._windows: dict[str, list[float]] = defaultdict(list)

    def is_rate_limited(self, key: str, max_requests: int, window_seconds: int = 60) -> bool:
        now = time.time()
        cutoff = now - window_seconds
        # Clean old entries
        self._windows[key] = [t for t in self._windows[key] if t > cutoff]
        if len(self._windows[key]) >= max_requests:
            return True
        self._windows[key].append(now)
        return False

    def cleanup_stale(self, max_age: int = 120):
        """Remove keys with no recent entries."""
        now = time.time()
        stale = [k for k, v in self._windows.items() if not v or v[-1] < now - max_age]
        for k in stale:
            del self._windows[k]

rate_limiter = RateLimiter()
