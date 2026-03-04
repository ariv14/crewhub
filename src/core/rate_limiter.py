"""Rate limiter with Redis backend and in-memory fallback.

Uses Redis INCR + EXPIRE for multi-instance deployments. Falls back to
in-memory sliding window when Redis is unavailable.
"""

import logging
import os
import time
from collections import defaultdict

from fastapi import Depends, Request

from src.config import settings
from src.core.auth import get_current_user_id
from src.core.exceptions import RateLimitError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Redis backend (optional)
# ---------------------------------------------------------------------------

_redis_client = None
_redis_init_attempted = False


def _get_redis():
    """Lazy-init Redis connection. Returns None if unavailable."""
    global _redis_client, _redis_init_attempted
    if _redis_init_attempted:
        return _redis_client

    _redis_init_attempted = True
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        return None

    try:
        import redis
        _redis_client = redis.from_url(redis_url, decode_responses=True)
        _redis_client.ping()
        logger.info("Redis rate limiter connected")
        return _redis_client
    except Exception:
        logger.warning("Redis unavailable, falling back to in-memory rate limiter")
        _redis_client = None
        return None


# ---------------------------------------------------------------------------
# In-memory backend
# ---------------------------------------------------------------------------


class RateLimiter:
    """Sliding window rate limiter with Redis or in-memory backend."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> bool:
        r = _get_redis()
        if r is not None:
            return self._check_redis(r, key)
        return self._check_memory(key)

    def _check_redis(self, r, key: str) -> bool:
        redis_key = f"ratelimit:{key}"
        try:
            current = r.incr(redis_key)
            if current == 1:
                r.expire(redis_key, self.window_seconds)
            return current <= self.max_requests
        except Exception:
            logger.warning("Redis check failed, falling back to in-memory")
            return self._check_memory(key)

    def _check_memory(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self.window_seconds
        timestamps = self._requests[key]
        self._requests[key] = [t for t in timestamps if t > window_start]

        if len(self._requests[key]) >= self.max_requests:
            return False

        self._requests[key].append(now)
        return True

    def get_limit_info(self, key: str) -> dict:
        r = _get_redis()
        if r is not None:
            return self._get_limit_info_redis(r, key)
        return self._get_limit_info_memory(key)

    def _get_limit_info_redis(self, r, key: str) -> dict:
        redis_key = f"ratelimit:{key}"
        try:
            current = int(r.get(redis_key) or 0)
            ttl = r.ttl(redis_key)
            remaining = max(0, self.max_requests - current)
            return {"remaining": remaining, "reset_in_seconds": max(ttl, 0)}
        except Exception:
            return self._get_limit_info_memory(key)

    def _get_limit_info_memory(self, key: str) -> dict:
        now = time.monotonic()
        window_start = now - self.window_seconds
        timestamps = self._requests.get(key, [])
        current = sum(1 for t in timestamps if t > window_start)
        remaining = max(0, self.max_requests - current)
        return {"remaining": remaining, "reset_in_seconds": self.window_seconds}


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

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
    request: Request,
    user_id=Depends(get_current_user_id),
) -> None:
    limiter = get_rate_limiter()
    key = str(user_id)
    allowed = limiter.check(key)
    info = limiter.get_limit_info(key)

    # Store rate limit info for response headers
    request.state.rate_limit_info = {
        "limit": limiter.max_requests,
        "remaining": info["remaining"],
        "reset": info["reset_in_seconds"],
    }

    if not allowed:
        raise RateLimitError(
            detail=f"Rate limit exceeded. Try again in {info['reset_in_seconds']} seconds"
        )


# Stricter limiter for unauthenticated endpoints (login, register)
_auth_limiter: RateLimiter | None = None


def _get_auth_limiter() -> RateLimiter:
    global _auth_limiter
    if _auth_limiter is None:
        _auth_limiter = RateLimiter(max_requests=20, window_seconds=60)
    return _auth_limiter


async def rate_limit_by_ip(request: Request) -> None:
    """Rate limit by client IP — for unauthenticated endpoints.

    Skipped during tests (pytest) to avoid false rate-limit hits from
    test fixtures that register/login many users from the same IP.
    """
    import sys
    if "pytest" in sys.modules:
        return
    client_ip = request.client.host if request.client else "unknown"
    limiter = _get_auth_limiter()
    if not limiter.check(f"ip:{client_ip}"):
        info = limiter.get_limit_info(f"ip:{client_ip}")
        raise RateLimitError(
            detail=f"Too many requests. Try again in {info['reset_in_seconds']} seconds"
        )
