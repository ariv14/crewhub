"""Tests for F4: Sparkline Stats — daily task counts per agent."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_agent_stats_empty(
    client: AsyncClient, auth_headers: dict, registered_agent: dict
):
    agent_id = registered_agent["id"]
    resp = await client.get(f"/api/v1/agents/{agent_id}/stats")

    assert resp.status_code == 200
    data = resp.json()
    assert data["daily_tasks"] == []


@pytest.mark.asyncio
async def test_agent_stats_with_tasks(
    client: AsyncClient, auth_headers: dict, registered_agent: dict
):
    agent_id = registered_agent["id"]
    skill_id = registered_agent["skills"][0]["id"]

    # Create tasks via the API so they count as provider tasks
    for _ in range(3):
        resp = await client.post(
            "/api/v1/tasks/",
            json={
                "provider_agent_id": agent_id,
                "skill_id": str(skill_id),
                "messages": [
                    {"role": "user", "parts": [{"type": "text", "content": "test"}]}
                ],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201

    resp = await client.get(f"/api/v1/agents/{agent_id}/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["daily_tasks"]) >= 1
    total_count = sum(d["count"] for d in data["daily_tasks"])
    assert total_count == 3


@pytest.mark.asyncio
async def test_agent_stats_404(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/agents/{fake_id}/stats")

    # Stats endpoint returns empty list for nonexistent agents (no 404)
    assert resp.status_code == 200
    assert resp.json()["daily_tasks"] == []


@pytest.mark.asyncio
async def test_agent_stats_unauthenticated(
    client: AsyncClient, registered_agent: dict
):
    agent_id = registered_agent["id"]
    resp = await client.get(f"/api/v1/agents/{agent_id}/stats")

    # Public endpoint — no auth required
    assert resp.status_code == 200
