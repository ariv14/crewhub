"""Tests for the agent detection / auto-discovery endpoint.

Tests cover:
1. Schema validation (DetectRequest URL validation, SSRF protection)
2. Successful detection with mocked httpx response
3. Error modes: unreachable, timeout, non-200, invalid JSON, missing fields
4. Partial card -> correct warnings
5. Pricing defaults in suggested_registration
6. Skills mapping (A2A format -> internal format)
"""

import os
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test_detect.db")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from pydantic import ValidationError

from src.schemas.detect import DetectRequest, DetectedSkill, DetectResponse


# ============================================================
# Sample agent card fixture (matches real A2A agent card format)
# ============================================================

SAMPLE_AGENT_CARD = {
    "name": "Text Summarizer",
    "description": "Summarizes text content into concise summaries",
    "url": "https://example.com",
    "version": "1.0.0",
    "capabilities": {"streaming": False, "pushNotifications": False},
    "skills": [
        {
            "id": "summarize",
            "name": "Summarize Text",
            "description": "Summarizes input text",
            "inputModes": ["text"],
            "outputModes": ["text"],
        },
        {
            "id": "bullet-points",
            "name": "Bullet Points",
            "description": "Extracts key bullet points",
            "inputModes": ["text"],
            "outputModes": ["text"],
        },
    ],
    "securitySchemes": [{"type": "apiKey"}],
    "defaultInputModes": ["text"],
    "defaultOutputModes": ["text"],
}


# ============================================================
# 1. Schema Validation Tests
# ============================================================


class TestDetectSchemas:
    """Test DetectRequest URL validation and SSRF protection."""

    def test_valid_https_url(self):
        req = DetectRequest(url="https://example.com")
        assert req.url == "https://example.com"

    def test_valid_http_url(self):
        req = DetectRequest(url="http://example.com")
        assert req.url == "http://example.com"

    def test_rejects_ftp_scheme(self):
        with pytest.raises(ValidationError, match="http or https"):
            DetectRequest(url="ftp://example.com")

    def test_rejects_no_hostname(self):
        with pytest.raises(ValidationError):
            DetectRequest(url="https://")

    def test_rejects_private_ip_in_prod(self):
        """In non-debug mode, private IPs should be rejected."""
        with patch("src.config.settings") as mock_settings:
            mock_settings.debug = False
            with pytest.raises(ValidationError, match="local|private|internal"):
                DetectRequest(url="http://192.168.1.1/agent")

    def test_rejects_localhost_in_prod(self):
        with patch("src.config.settings") as mock_settings:
            mock_settings.debug = False
            with pytest.raises(ValidationError, match="local|private|internal"):
                DetectRequest(url="http://localhost:8000")

    def test_allows_localhost_in_debug(self):
        """In debug mode, localhost is allowed for local dev."""
        with patch("src.config.settings") as mock_settings:
            mock_settings.debug = True
            req = DetectRequest(url="http://localhost:8000")
            assert "localhost" in req.url

    def test_detected_skill_defaults(self):
        skill = DetectedSkill(
            skill_key="test", name="Test", description="A test skill"
        )
        assert skill.input_modes == ["text"]
        assert skill.output_modes == ["text"]

    def test_detect_response_defaults(self):
        resp = DetectResponse(
            name="Agent",
            description="Desc",
            url="https://example.com",
            version="1.0.0",
            suggested_registration={},
            card_url="https://example.com/.well-known/agent-card.json",
        )
        assert resp.skills == []
        assert resp.warnings == []
        assert resp.capabilities == {}


# ============================================================
# 2. Endpoint Tests (mocked httpx)
# ============================================================


def _mock_httpx_response(json_data=None, status_code=200, raise_exc=None):
    """Create a mock httpx response or exception."""

    async def mock_get(url, **kwargs):
        if raise_exc:
            raise raise_exc
        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = json_data
        return resp

    return mock_get


@pytest.mark.asyncio
class TestDetectEndpoint:
    """Test the POST /agents/detect endpoint."""

    async def _call_detect(self, payload: dict, mock_get=None):
        from src.core.auth import get_current_user
        from httpx import AsyncClient, ASGITransport
        from src.main import app

        fake_user = {"id": str(uuid.uuid4()), "firebase_uid": None}
        app.dependency_overrides[get_current_user] = lambda: fake_user

        if mock_get:
            patcher = patch("src.api.detect.httpx.AsyncClient")
            mock_client_cls = patcher.start()
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = mock_get
            mock_client_cls.return_value = mock_client

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post("/api/v1/agents/detect", json=payload)
        finally:
            app.dependency_overrides.clear()
            if mock_get:
                patcher.stop()

        return resp

    async def test_successful_detection(self):
        """Full agent card is parsed correctly."""
        mock_get = _mock_httpx_response(json_data=SAMPLE_AGENT_CARD)
        resp = await self._call_detect(
            {"url": "https://example.com"}, mock_get=mock_get
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Text Summarizer"
        assert data["description"] == "Summarizes text content into concise summaries"
        assert data["version"] == "1.0.0"
        assert len(data["skills"]) == 2
        assert data["skills"][0]["skill_key"] == "summarize"
        assert data["skills"][0]["name"] == "Summarize Text"
        assert data["skills"][1]["skill_key"] == "bullet-points"
        assert data["card_url"] == "https://example.com/.well-known/agent-card.json"
        assert data["warnings"] == []

        # Check suggested_registration is AgentCreate-compatible
        reg = data["suggested_registration"]
        assert reg["name"] == "Text Summarizer"
        assert reg["endpoint"] == "https://example.com"
        assert len(reg["skills"]) == 2
        assert reg["pricing"]["license_type"] == "open"
        assert reg["pricing"]["credits"] == 1

    async def test_strips_trailing_slash(self):
        """URL trailing slash is stripped before appending card path."""
        mock_get = _mock_httpx_response(json_data=SAMPLE_AGENT_CARD)
        resp = await self._call_detect(
            {"url": "https://example.com/"}, mock_get=mock_get
        )
        assert resp.status_code == 200
        assert resp.json()["card_url"] == "https://example.com/.well-known/agent-card.json"

    async def test_unreachable_endpoint(self):
        import httpx as httpx_mod

        mock_get = _mock_httpx_response(raise_exc=httpx_mod.ConnectError("refused"))
        resp = await self._call_detect(
            {"url": "https://unreachable.example.com"}, mock_get=mock_get
        )
        assert resp.status_code == 400
        assert "Could not reach endpoint" in resp.json()["detail"]

    async def test_timeout(self):
        import httpx as httpx_mod

        mock_get = _mock_httpx_response(raise_exc=httpx_mod.ReadTimeout("timeout"))
        resp = await self._call_detect(
            {"url": "https://slow.example.com"}, mock_get=mock_get
        )
        assert resp.status_code == 400
        assert "timed out" in resp.json()["detail"]

    async def test_non_200_response(self):
        mock_get = _mock_httpx_response(status_code=404)
        resp = await self._call_detect(
            {"url": "https://example.com"}, mock_get=mock_get
        )
        assert resp.status_code == 400
        assert "HTTP 404" in resp.json()["detail"]

    async def test_invalid_json(self):
        """Non-JSON response should return 400."""

        async def bad_json(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            resp.json.side_effect = ValueError("not json")
            return resp

        resp = await self._call_detect(
            {"url": "https://example.com"}, mock_get=bad_json
        )
        assert resp.status_code == 400
        assert "not valid JSON" in resp.json()["detail"]

    async def test_missing_name(self):
        """Agent card without 'name' field should fail."""
        card = {"description": "No name", "version": "1.0.0"}
        mock_get = _mock_httpx_response(json_data=card)
        resp = await self._call_detect(
            {"url": "https://example.com"}, mock_get=mock_get
        )
        assert resp.status_code == 400
        assert "missing required field: name" in resp.json()["detail"]

    async def test_partial_card_generates_warnings(self):
        """Card with missing description and no skills triggers warnings."""
        card = {"name": "Minimal Agent"}
        mock_get = _mock_httpx_response(json_data=card)
        resp = await self._call_detect(
            {"url": "https://example.com"}, mock_get=mock_get
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Minimal Agent"
        assert "Missing description" in data["warnings"]
        assert "No skills found" in data["warnings"]

    async def test_pricing_defaults(self):
        """suggested_registration should have open/per_task/1 credit defaults."""
        card = {"name": "Agent", "description": "Test", "skills": []}
        mock_get = _mock_httpx_response(json_data=card)
        resp = await self._call_detect(
            {"url": "https://example.com"}, mock_get=mock_get
        )
        reg = resp.json()["suggested_registration"]
        assert reg["pricing"]["license_type"] == "open"
        assert reg["pricing"]["model"] == "per_task"
        assert reg["pricing"]["credits"] == 1

    async def test_url_validation_rejects_invalid(self):
        """Invalid URL scheme should be rejected at schema level (422)."""
        resp = await self._call_detect({"url": "ftp://example.com"})
        assert resp.status_code == 422

    async def test_public_no_auth_required(self):
        """Detect endpoint is public — no auth needed."""
        from httpx import AsyncClient, ASGITransport
        from src.main import app

        # Don't override get_current_user — should still work (public endpoint)
        app.dependency_overrides.clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/agents/detect",
                json={"url": "https://example.com"},
            )
        # 400 = endpoint unreachable (not 401/403), proving no auth required
        assert resp.status_code == 400

    async def test_non_dict_json_response(self):
        """JSON that isn't an object (e.g. array) should fail."""
        mock_get = _mock_httpx_response(json_data=["not", "an", "object"])
        resp = await self._call_detect(
            {"url": "https://example.com"}, mock_get=mock_get
        )
        assert resp.status_code == 400
        assert "not valid JSON" in resp.json()["detail"]
