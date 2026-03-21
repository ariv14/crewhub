import time

class InMemoryRateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self._counters: dict[str, list[float]] = {}
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def is_limited(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        hits = self._counters.get(key, [])
        hits = [t for t in hits if t > cutoff]
        hits.append(now)
        self._counters[key] = hits
        return len(hits) > self.max_requests

    def cleanup(self):
        """Remove expired entries to prevent memory growth."""
        now = time.time()
        cutoff = now - self.window_seconds
        self._counters = {
            k: [t for t in v if t > cutoff]
            for k, v in self._counters.items()
            if any(t > cutoff for t in v)
        }
