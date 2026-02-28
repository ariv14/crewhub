"""Tests for F3: Task Status History — timeline tracking on tasks."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import _make_agent_payload


async def _create_task(client: AsyncClient, auth_headers: dict) -> dict:
    """Helper: register an agent and create a task against it."""
    payload = _make_agent_payload(name="Timeline Agent")
    agent_resp = await client.post("/api/v1/agents/", json=payload, headers=auth_headers)
    assert agent_resp.status_code == 201
    agent = agent_resp.json()
    skill_id = agent["skills"][0]["id"]

    task_resp = await client.post(
        "/api/v1/tasks/",
        json={
            "provider_agent_id": agent["id"],
            "skill_id": str(skill_id),
            "messages": [
                {"role": "user", "parts": [{"type": "text", "content": "Test input"}]}
            ],
        },
        headers=auth_headers,
    )
    assert task_resp.status_code == 201
    return task_resp.json()


@pytest.mark.asyncio
async def test_task_has_status_history_on_creation(
    client: AsyncClient, auth_headers: dict
):
    task = await _create_task(client, auth_headers)

    assert "status_history" in task
    assert len(task["status_history"]) >= 1
    assert task["status_history"][0]["status"] in ("submitted", "pending_payment")


@pytest.mark.asyncio
async def test_status_history_appends_on_cancel(
    client: AsyncClient, auth_headers: dict
):
    task = await _create_task(client, auth_headers)
    task_id = task["id"]

    cancel_resp = await client.post(
        f"/api/v1/tasks/{task_id}/cancel", headers=auth_headers
    )
    assert cancel_resp.status_code == 200
    cancelled = cancel_resp.json()

    assert len(cancelled["status_history"]) >= 2
    statuses = [h["status"] for h in cancelled["status_history"]]
    assert "canceled" in statuses


@pytest.mark.asyncio
async def test_status_history_format(client: AsyncClient, auth_headers: dict):
    task = await _create_task(client, auth_headers)

    for entry in task["status_history"]:
        assert "status" in entry
        assert "at" in entry


@pytest.mark.asyncio
async def test_status_history_in_task_response(
    client: AsyncClient, auth_headers: dict
):
    task = await _create_task(client, auth_headers)
    task_id = task["id"]

    get_resp = await client.get(f"/api/v1/tasks/{task_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert "status_history" in data
    assert len(data["status_history"]) >= 1
