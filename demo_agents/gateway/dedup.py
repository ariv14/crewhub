import time

class MessageDedup:
    def __init__(self, ttl: int = 300):
        self._seen: dict[str, float] = {}
        self.ttl = ttl

    def is_duplicate(self, connection_id: str, message_id: str) -> bool:
        key = f"{connection_id}:{message_id}"
        now = time.time()
        # Periodic cleanup
        if len(self._seen) > 10000:
            self._seen = {k: v for k, v in self._seen.items() if now - v < self.ttl}
        if key in self._seen:
            return True
        self._seen[key] = now
        return False
