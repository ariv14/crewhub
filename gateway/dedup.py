"""Message deduplication."""
import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)

class MessageDedup:
    """In-memory dedup cache. DB unique constraint is the real guarantee."""

    def __init__(self, max_size: int = 10000):
        self._seen: OrderedDict[str, bool] = OrderedDict()
        self._max_size = max_size

    def is_duplicate(self, connection_id: str, platform_message_id: str, direction: str = "inbound") -> bool:
        key = f"{connection_id}:{platform_message_id}:{direction}"
        if key in self._seen:
            return True
        self._seen[key] = True
        if len(self._seen) > self._max_size:
            self._seen.popitem(last=False)
        return False

dedup = MessageDedup()
