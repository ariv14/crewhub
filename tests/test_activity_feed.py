"""Tests for F1: SSE Activity Feed — live platform events."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@pytest.mark.asyncio
async def test_activity_stream_returns_sse(
    client: AsyncClient, auth_headers: dict, engine
):
    """GET /activity/stream should return text/event-stream content-type."""
    # Patch the module-level async_session used inside the SSE generator
    patched_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    with patch("src.api.activity.async_session", patched_session):
        resp = await client.get("/api/v1/activity/stream", headers=auth_headers)

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_activity_stream_requires_auth(client: AsyncClient):
    """No auth token → 401."""
    resp = await client.get("/api/v1/activity/stream")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_activity_stream_emits_agent_event(
    client: AsyncClient, auth_headers: dict, engine
):
    """After registering an agent, the SSE stream should contain an agent_registered event."""
    from tests.conftest import _make_agent_payload

    # Register an agent first so there's data to emit
    payload = _make_agent_payload(name="SSE Test Agent")
    reg = await client.post("/api/v1/agents/", json=payload, headers=auth_headers)
    assert reg.status_code == 201

    # Patch the module-level async_session and read the stream
    patched_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    with patch("src.api.activity.async_session", patched_session):
        with patch("src.api.activity.SSE_MAX_DURATION", 1):
            resp = await client.get("/api/v1/activity/stream", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.text
    assert "agent_registered" in body
    assert "SSE Test Agent" in body
