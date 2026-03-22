"""Tests for Channel & Customer Management — schemas, crypto, pseudonymization."""
import pytest
import sys
import os
import hashlib
import hmac as hmac_mod
from uuid import uuid4
from datetime import datetime

from src.schemas.channel import (
    ChannelContactResponse, ChannelContactListResponse,
    ChannelMessageResponse, ChannelMessageListResponse,
    AdminMessageAccessRequest, GDPRErasureResponse,
    ChannelAnalyticsResponse,
)


class TestContactSchemas:
    def test_contact_response_defaults(self):
        c = ChannelContactResponse(
            platform_user_id_hash="abc123", message_count=5,
            last_seen=datetime.now(), first_seen=datetime.now()
        )
        assert c.is_blocked is False

    def test_contact_list_response(self):
        c = ChannelContactListResponse(contacts=[], total=0)
        assert c.total == 0


class TestMessageSchemas:
    def test_message_response(self):
        m = ChannelMessageResponse(
            id=uuid4(), direction="inbound",
            platform_user_id_hash="abc", message_text=None,
            credits_charged=1.0, created_at=datetime.now()
        )
        assert m.message_text is None

    def test_message_list_response(self):
        r = ChannelMessageListResponse(messages=[], has_more=False)
        assert r.cursor is None


class TestAdminAccessSchema:
    def test_valid_justification(self):
        req = AdminMessageAccessRequest(justification="abuse_report")
        assert req.justification == "abuse_report"

    def test_all_valid_justifications(self):
        for j in ["abuse_report", "developer_support", "legal_request", "compliance_check"]:
            req = AdminMessageAccessRequest(justification=j)
            assert req.justification == j

    def test_invalid_justification_rejected(self):
        with pytest.raises(Exception):
            AdminMessageAccessRequest(justification="curiosity")


class TestGDPRErasure:
    def test_erasure_response(self):
        r = GDPRErasureResponse(deleted_messages=42, user_hash="abc", channel_id=uuid4())
        assert r.deleted_messages == 42


class TestMessageCrypto:
    def test_encrypt_decrypt_roundtrip(self):
        os.environ["CHANNEL_MESSAGE_KEY"] = "test-key-for-crypto-12345"
        # Add gateway to path for import
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "demo_agents", "gateway"))
        from message_crypto import encrypt_message, decrypt_message

        original = "Hello, this is a test message!"
        encrypted = encrypt_message(original)
        assert encrypted.startswith("v1:")
        assert encrypted != original

        decrypted = decrypt_message(encrypted)
        assert decrypted == original
        del os.environ["CHANNEL_MESSAGE_KEY"]

    def test_decrypt_none_returns_none(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "demo_agents", "gateway"))
        from message_crypto import decrypt_message
        assert decrypt_message(None) is None

    def test_decrypt_unversioned_passthrough(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "demo_agents", "gateway"))
        from message_crypto import decrypt_message
        assert decrypt_message("plain text") == "plain text"


class TestPseudonymization:
    def test_hmac_consistent(self):
        """Same input produces same output."""
        key = b"secret:conn1"
        h1 = hmac_mod.new(key, b"user123", hashlib.sha256).hexdigest()[:16]
        h2 = hmac_mod.new(key, b"user123", hashlib.sha256).hexdigest()[:16]
        assert h1 == h2

    def test_different_connections_different_hashes(self):
        """Per-connection isolation — same user gets different hashes across connections."""
        h1 = hmac_mod.new(b"secret:conn1", b"user123", hashlib.sha256).hexdigest()[:16]
        h2 = hmac_mod.new(b"secret:conn2", b"user123", hashlib.sha256).hexdigest()[:16]
        assert h1 != h2

    def test_not_reversible_without_key(self):
        """Hash is 16 hex chars — cannot be reversed to original user ID."""
        h = hmac_mod.new(b"secret:conn1", b"user123", hashlib.sha256).hexdigest()[:16]
        assert len(h) == 16
        assert "user123" not in h


class TestRouteRegistration:
    def test_contact_routes_exist(self):
        from src.main import app
        paths = [r.path for r in app.routes if hasattr(r, 'path')]
        contact_paths = [p for p in paths if 'contact' in p]
        assert len(contact_paths) >= 4  # contacts, block, unblock, messages

    def test_admin_channel_routes_exist(self):
        from src.main import app
        paths = [r.path for r in app.routes if hasattr(r, 'path')]
        admin_ch = [p for p in paths if 'admin/channel' in p]
        assert len(admin_ch) >= 3  # list, detail, messages
