"""Redis-backed sliding window rate limiter."""

import time

import redis.asyncio as redis
from fastapi import Depends

from src.config import settings
from src.core.auth import get_current_user_id
from src.core.exceptions import RateLimitError


class RateLimiter:
    """Sliding window rate limiter backed by Redis sorted sets."""

    def __init__(
        self,
        redis_url: str,
        max_requests: int = 100,
        window_seconds: int = 60,
    ):
        """Initialize the rate limiter.

        Args:
            redis_url: Redis connection URL.
            max_requests: Maximum number of requests allowed in the window.
            window_seconds: Size of the sliding window in seconds.
        """
        self.redis_url = redis_url
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._redis: redis.Redis | None = None

    async def _get_redis(self) -> redis.Redis:
        """Lazily create and return a Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    async def check(self, key: str) -> bool:
        """Check whether a request is allowed under the rate limit.

        Uses a sorted set where each member is a unique timestamp-based ID and
        the score is the timestamp. Old entries outside the window are pruned.

        Args:
            key: A unique identifier for the rate limit bucket (e.g., user ID).

        Returns:
            True if the request is allowed, False if the limit is exceeded.
        """
        r = await self._get_redis()
        now = time.time()
        window_start = now - self.window_seconds
        rate_key = f"rate_limit:{key}"

        pipe = r.pipeline()
        # Remove entries outside the current window
        pipe.zremrangebyscore(rate_key, 0, window_start)
        # Count remaining entries
        pipe.zcard(rate_key)
        # Add current request
        pipe.zadd(rate_key, {f"{now}": now})
        # Set expiry on the key to auto-cleanup
        pipe.expire(rate_key, self.window_seconds)
        results = await pipe.execute()

        current_count = results[1]
        return current_count < self.max_requests

    async def get_limit_info(self, key: str) -> dict:
        """Get rate limit information for a given key.

        Args:
            key: The rate limit bucket identifier.

        Returns:
            dict with 'remaining' (int) and 'reset_at' (float, UNIX timestamp).
        """
        r = await self._get_redis()
        now = time.time()
        window_start = now - self.window_seconds
        rate_key = f"rate_limit:{key}"

        pipe = r.pipeline()
        pipe.zremrangebyscore(rate_key, 0, window_start)
        pipe.zcard(rate_key)
        results = await pipe.execute()

        current_count = results[1]
        remaining = max(0, self.max_requests - current_count)
        reset_at = now + self.window_seconds

        return {
            "remaining": remaining,
            "reset_at": reset_at,
        }

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None


# Module-level singleton instance
_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the module-level RateLimiter singleton."""
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter(
            redis_url=settings.redis_url,
            max_requests=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )
    return _limiter


async def rate_limit_dependency(
    user_id=Depends(get_current_user_id),
) -> None:
    """FastAPI dependency that enforces rate limiting per user.

    Raises:
        RateLimitError: If the user has exceeded the rate limit.
    """
    limiter = get_rate_limiter()
    allowed = await limiter.check(str(user_id))
    if not allowed:
        info = await limiter.get_limit_info(str(user_id))
        raise RateLimitError(
            detail=f"Rate limit exceeded. Try again in {int(info['reset_at'] - time.time())} seconds"
        )
