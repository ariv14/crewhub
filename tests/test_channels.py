"""Tests for Multi-Channel Gateway endpoints and schemas."""
import pytest
from uuid import uuid4
from src.schemas.channel import (
    GatewayChargeRequest, GatewayChargeResponse,
    GatewayLogMessageRequest, GatewayHeartbeatRequest,
    GatewayConnectionResponse, ChannelCreate, ChannelResponse,
)


class TestGatewaySchemas:
    """Verify gateway Pydantic schemas validate correctly."""

    def test_charge_request_valid(self):
        req = GatewayChargeRequest(
            connection_id=uuid4(), platform_user_id="user123",
            credits=5.0, message_text="test"
        )
        assert req.credits == 5.0

    def test_charge_request_rejects_zero_credits(self):
        with pytest.raises(Exception):
            GatewayChargeRequest(
                connection_id=uuid4(), platform_user_id="user123",
                credits=0, message_text="test"
            )

    def test_charge_request_rejects_over_100_credits(self):
        with pytest.raises(Exception):
            GatewayChargeRequest(
                connection_id=uuid4(), platform_user_id="user123",
                credits=101, message_text="test"
            )

    def test_charge_response(self):
        resp = GatewayChargeResponse(success=True, remaining_balance=100.0, today_usage=5.0)
        assert resp.success is True

    def test_log_message_valid(self):
        req = GatewayLogMessageRequest(
            connection_id=uuid4(), platform_user_id="user123",
            platform_message_id="msg456", direction="inbound",
            message_text="hello"
        )
        assert req.direction == "inbound"

    def test_log_message_rejects_invalid_direction(self):
        with pytest.raises(Exception):
            GatewayLogMessageRequest(
                connection_id=uuid4(), platform_user_id="user123",
                platform_message_id="msg456", direction="invalid",
                message_text="hello"
            )

    def test_connection_response(self):
        resp = GatewayConnectionResponse(
            id=uuid4(), owner_id=uuid4(), platform="telegram",
            bot_token="decrypted_token", agent_id=uuid4(),
            status="active"
        )
        assert resp.platform == "telegram"
        assert resp.pause_on_limit is True  # default

    def test_heartbeat_request(self):
        req = GatewayHeartbeatRequest(connections=[
            {"connection_id": str(uuid4()), "status": "active"}
        ])
        assert len(req.connections) == 1


class TestGatewayAuth:
    """Verify gateway auth dependency exists and is importable."""

    def test_gateway_router_importable(self):
        from src.api.gateway import router
        assert router is not None

    def test_gateway_key_dependency_importable(self):
        from src.api.gateway import require_gateway_key
        assert callable(require_gateway_key)


class TestChannelServiceImports:
    """Verify channel service methods exist."""

    def test_rotate_token_method_exists(self):
        from src.services.channel_service import ChannelService
        assert hasattr(ChannelService, 'rotate_token')

    def test_get_analytics_method_exists(self):
        from src.services.channel_service import ChannelService
        assert hasattr(ChannelService, 'get_analytics')
