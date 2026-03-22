"""Tests for the CrewHub Gateway service components."""
import sys
import os
import time
import pytest

# Add gateway to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "demo_agents", "gateway"))


class TestTelegramAdapter:
    """Test Telegram webhook parsing and message formatting."""

    def test_parse_text_message(self):
        from adapters.telegram import TelegramAdapter
        adapter = TelegramAdapter()

        body = {
            "update_id": 123,
            "message": {
                "message_id": 456,
                "from": {"id": 789, "first_name": "Test"},
                "chat": {"id": 101112, "type": "private"},
                "text": "Hello agent!",
            }
        }
        msg = adapter.parse_inbound(body)
        assert msg is not None
        assert msg.text == "Hello agent!"
        assert msg.platform_user_id == "789"
        assert msg.platform_message_id == "456"
        assert msg.platform_chat_id == "101112"

    def test_parse_non_text_returns_none(self):
        from adapters.telegram import TelegramAdapter
        adapter = TelegramAdapter()

        body = {
            "update_id": 123,
            "message": {
                "message_id": 456,
                "from": {"id": 789},
                "chat": {"id": 101112},
                "photo": [{"file_id": "abc"}],
            }
        }
        msg = adapter.parse_inbound(body)
        assert msg is None

    def test_parse_empty_update_returns_none(self):
        from adapters.telegram import TelegramAdapter
        adapter = TelegramAdapter()

        msg = adapter.parse_inbound({"update_id": 123})
        assert msg is None

    def test_parse_edited_message(self):
        from adapters.telegram import TelegramAdapter
        adapter = TelegramAdapter()

        body = {
            "update_id": 123,
            "edited_message": {
                "message_id": 456,
                "from": {"id": 789},
                "chat": {"id": 101112},
                "text": "Edited text",
            }
        }
        msg = adapter.parse_inbound(body)
        assert msg is not None
        assert msg.text == "Edited text"

    def test_verify_webhook_always_true(self):
        from adapters.telegram import TelegramAdapter
        adapter = TelegramAdapter()
        assert adapter.verify_webhook(b"", {}) is True

    def test_ack_response(self):
        from adapters.telegram import TelegramAdapter
        adapter = TelegramAdapter()
        assert adapter.ack_response() == {"ok": True}


class TestRateLimiter:
    """Test in-memory rate limiting."""

    def test_allows_under_limit(self):
        from rate_limiter import InMemoryRateLimiter
        rl = InMemoryRateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            assert rl.is_limited("user1") is False

    def test_blocks_over_limit(self):
        from rate_limiter import InMemoryRateLimiter
        rl = InMemoryRateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            rl.is_limited("user1")
        assert rl.is_limited("user1") is True

    def test_independent_users(self):
        from rate_limiter import InMemoryRateLimiter
        rl = InMemoryRateLimiter(max_requests=2, window_seconds=60)
        rl.is_limited("user1")
        rl.is_limited("user1")
        assert rl.is_limited("user1") is True
        assert rl.is_limited("user2") is False

    def test_cleanup(self):
        from rate_limiter import InMemoryRateLimiter
        rl = InMemoryRateLimiter(max_requests=10, window_seconds=1)
        rl.is_limited("user1")
        time.sleep(1.1)
        rl.cleanup()
        assert "user1" not in rl._counters or len(rl._counters["user1"]) == 0


class TestMessageDedup:
    """Test message deduplication."""

    def test_first_message_not_duplicate(self):
        from dedup import MessageDedup
        d = MessageDedup(ttl=60)
        assert d.is_duplicate("conn1", "msg1") is False

    def test_same_message_is_duplicate(self):
        from dedup import MessageDedup
        d = MessageDedup(ttl=60)
        d.is_duplicate("conn1", "msg1")
        assert d.is_duplicate("conn1", "msg1") is True

    def test_different_connections_not_duplicate(self):
        from dedup import MessageDedup
        d = MessageDedup(ttl=60)
        d.is_duplicate("conn1", "msg1")
        assert d.is_duplicate("conn2", "msg1") is False

    def test_expired_not_duplicate(self):
        from dedup import MessageDedup
        d = MessageDedup(ttl=1)
        d.is_duplicate("conn1", "msg1")
        time.sleep(1.1)
        # Force cleanup by inserting enough entries to exceed the 10000 threshold
        for i in range(10001):
            d._seen[f"cleanup_{i}"] = 0
        assert d.is_duplicate("conn1", "msg1") is False


class TestAdapterRegistry:
    """Test adapter lookup."""

    def test_telegram_adapter_exists(self):
        from adapters import get_adapter
        adapter = get_adapter("telegram")
        assert adapter is not None

    def test_unknown_platform_raises(self):
        from adapters import get_adapter
        with pytest.raises(ValueError, match="Unsupported platform"):
            get_adapter("myspace")
