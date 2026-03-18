# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Abuse detection service — identifies and blocks suspicious activity.

Tracks:
- Rapid task creation (> N tasks/minute per user)
- Uses Redis sorted sets with TTL for sliding windows.
- Falls back to in-memory tracking when Redis is unavailable.
"""

import logging
import time
from collections import defaultdict

from src.config import settings
from src.core.exceptions import AbuseDetectedError

logger = logging.getLogger(__name__)

# In-memory fallback: {user_id: [timestamp, ...]}
_task_creation_times: dict[str, list[float]] = defaultdict(list)


def check_task_creation_rate(user_id: str) -> None:
    """Check if user is creating tasks too rapidly.

    Raises AbuseDetectedError if rate exceeds threshold.
    """
    if not settings.abuse_detection_enabled:
        return

    max_per_minute = settings.abuse_max_tasks_per_minute
    now = time.time()
    window = 60.0  # 1 minute

    try:
        from src.core.rate_limiter import _get_redis
        redis = _get_redis()
        if redis:
            _check_rate_redis(redis, user_id, max_per_minute, now, window)
            return
    except Exception:
        pass

    # In-memory fallback
    _check_rate_memory(user_id, max_per_minute, now, window)


def _check_rate_redis(redis, user_id: str, limit: int, now: float, window: float) -> None:
    """Check rate using Redis sorted set."""
    key = f"abuse:tasks:{user_id}"
    cutoff = now - window

    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, "-inf", cutoff)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, int(window) + 10)
    results = pipe.execute()

    count = results[2]
    if count > limit:
        logger.warning(
            "Abuse detected: user %s created %d tasks in last minute (limit: %d)",
            user_id, count, limit,
        )
        raise AbuseDetectedError(
            detail=f"Rate limit exceeded: maximum {limit} tasks per minute. "
            "Please slow down and try again."
        )


def _check_rate_memory(user_id: str, limit: int, now: float, window: float) -> None:
    """Check rate using in-memory sliding window."""
    cutoff = now - window
    timestamps = _task_creation_times[user_id]

    # Prune old entries
    _task_creation_times[user_id] = [t for t in timestamps if t > cutoff]
    _task_creation_times[user_id].append(now)

    if len(_task_creation_times[user_id]) > limit:
        logger.warning(
            "Abuse detected (in-memory): user %s created %d tasks in last minute (limit: %d)",
            user_id, len(_task_creation_times[user_id]), limit,
        )
        raise AbuseDetectedError(
            detail=f"Rate limit exceeded: maximum {limit} tasks per minute. "
            "Please slow down and try again."
        )


def reset_user(user_id: str) -> None:
    """Reset abuse tracking for a user (for testing)."""
    _task_creation_times.pop(user_id, None)
    try:
        from src.core.rate_limiter import _get_redis
        redis = _get_redis()
        if redis:
            redis.delete(f"abuse:tasks:{user_id}")
    except Exception:
        pass
