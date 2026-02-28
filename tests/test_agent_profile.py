"""Tests for F6: Agent Config Upgrade — avatar, conversation starters, test cases."""

import pytest
from httpx import AsyncClient

from tests.conftest import _make_agent_payload


@pytest.mark.asyncio
async def test_register_agent_with_avatar(client: AsyncClient, auth_headers: dict):
    payload = _make_agent_payload(avatar_url="https://example.com/avatar.png")
    resp = await client.post("/api/v1/agents/", json=payload, headers=auth_headers)

    assert resp.status_code == 201
    data = resp.json()
    assert data["avatar_url"] == "https://example.com/avatar.png"


@pytest.mark.asyncio
async def test_register_agent_with_conversation_starters(
    client: AsyncClient, auth_headers: dict
):
    starters = ["Summarize this doc", "Translate to French", "Help me debug"]
    payload = _make_agent_payload(conversation_starters=starters)
    resp = await client.post("/api/v1/agents/", json=payload, headers=auth_headers)

    assert resp.status_code == 201
    data = resp.json()
    assert data["conversation_starters"] == starters


@pytest.mark.asyncio
async def test_register_agent_with_test_cases(client: AsyncClient, auth_headers: dict):
    cases = [
        {"input": "Hello world", "expected": "Summarized text"},
        {"input": "Long document...", "expected": "Brief summary"},
    ]
    payload = _make_agent_payload(test_cases=cases)
    resp = await client.post("/api/v1/agents/", json=payload, headers=auth_headers)

    assert resp.status_code == 201
    data = resp.json()
    assert data["test_cases"] == cases


@pytest.mark.asyncio
async def test_avatar_url_defaults_null(client: AsyncClient, auth_headers: dict):
    payload = _make_agent_payload()
    resp = await client.post("/api/v1/agents/", json=payload, headers=auth_headers)

    assert resp.status_code == 201
    assert resp.json()["avatar_url"] is None


@pytest.mark.asyncio
async def test_update_agent_avatar(client: AsyncClient, auth_headers: dict):
    # Create agent without avatar
    payload = _make_agent_payload()
    create_resp = await client.post("/api/v1/agents/", json=payload, headers=auth_headers)
    assert create_resp.status_code == 201
    agent_id = create_resp.json()["id"]

    # Update with avatar
    update_resp = await client.put(
        f"/api/v1/agents/{agent_id}",
        json={"avatar_url": "https://cdn.example.com/new-avatar.jpg"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["avatar_url"] == "https://cdn.example.com/new-avatar.jpg"


@pytest.mark.asyncio
async def test_invalid_avatar_url_rejected(client: AsyncClient, auth_headers: dict):
    payload = _make_agent_payload(avatar_url="ftp://invalid-scheme.com/avatar.png")
    resp = await client.post("/api/v1/agents/", json=payload, headers=auth_headers)

    assert resp.status_code == 422
