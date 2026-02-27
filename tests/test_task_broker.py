"""Tests for the task lifecycle endpoints (/api/v1/tasks)."""

import pytest
from httpx import AsyncClient

from tests.conftest import _make_agent_payload


async def _register_two_agents(
    client: AsyncClient, auth_headers: dict
) -> tuple[dict, dict]:
    """Helper: register a client agent and a provider agent, return both."""
    client_payload = _make_agent_payload(
        name="Client Agent",
        description="Agent that delegates tasks",
        category="orchestration",
    )
    provider_payload = _make_agent_payload(
        name="Provider Agent",
        description="Agent that handles tasks",
        category="analytics",
        skills=[
            {
                "skill_key": "analyze-data",
                "name": "Analyze Data",
                "description": "Run statistical analysis on datasets",
                "input_modes": ["text", "data"],
                "output_modes": ["text"],
                "examples": [],
                "avg_credits": 10.0,
                "avg_latency_ms": 5000,
            }
        ],
        pricing={"model": "per_task", "credits": 10.0},
    )

    resp_c = await client.post(
        "/api/v1/agents/", json=client_payload, headers=auth_headers
    )
    resp_p = await client.post(
        "/api/v1/agents/", json=provider_payload, headers=auth_headers
    )
    assert resp_c.status_code == 201, f"Client agent registration failed: {resp_c.text}"
    assert resp_p.status_code == 201, f"Provider agent registration failed: {resp_p.text}"

    return resp_c.json(), resp_p.json()


async def _create_task(
    client: AsyncClient,
    auth_headers: dict,
    client_agent: dict,
    provider_agent: dict,
) -> dict:
    """Helper: create a task from client_agent to provider_agent."""
    skill_key = provider_agent["skills"][0]["skill_key"]
    task_payload = {
        "provider_agent_id": provider_agent["id"],
        "skill_id": skill_key,
        "messages": [
            {
                "role": "user",
                "parts": [{"type": "text", "content": "Please analyze this data."}],
            }
        ],
        "max_credits": 10.0,
    }
    resp = await client.post(
        "/api/v1/tasks/", json=task_payload, headers=auth_headers
    )
    assert resp.status_code == 201, f"Task creation failed: {resp.text}"
    return resp.json()


# ------------------------------------------------------------------
# POST /api/v1/tasks/ -- create a task
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_task(client: AsyncClient, auth_headers: dict):
    """Creating a task between two agents should return status=submitted."""
    client_agent, provider_agent = await _register_two_agents(client, auth_headers)
    task = await _create_task(client, auth_headers, client_agent, provider_agent)

    assert "id" in task
    assert task["status"] == "submitted"
    assert task["provider_agent_id"] == provider_agent["id"]
    assert task["skill_id"] is not None
    assert isinstance(task["messages"], list)
    assert len(task["messages"]) >= 1


# ------------------------------------------------------------------
# GET /api/v1/tasks/{id} -- get task details
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_task(client: AsyncClient, auth_headers: dict):
    """Getting a task by ID should return its full details."""
    client_agent, provider_agent = await _register_two_agents(client, auth_headers)
    task = await _create_task(client, auth_headers, client_agent, provider_agent)

    resp = await client.get(
        f"/api/v1/tasks/{task['id']}", headers=auth_headers
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["id"] == task["id"]
    assert data["status"] == "submitted"
    assert data["provider_agent_id"] == provider_agent["id"]


# ------------------------------------------------------------------
# POST /api/v1/tasks/{id}/cancel -- cancel a task
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancel_task(client: AsyncClient, auth_headers: dict):
    """Canceling a submitted task should set its status to canceled."""
    client_agent, provider_agent = await _register_two_agents(client, auth_headers)
    task = await _create_task(client, auth_headers, client_agent, provider_agent)

    resp = await client.post(
        f"/api/v1/tasks/{task['id']}/cancel", headers=auth_headers
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "canceled"


# ------------------------------------------------------------------
# POST /api/v1/tasks/{id}/rate -- rate a completed task
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rate_task(client: AsyncClient, auth_headers: dict, db_session):
    """Rating a completed task should store the score."""
    from src.models.task import Task, TaskStatus
    from datetime import datetime, timezone

    client_agent, provider_agent = await _register_two_agents(client, auth_headers)
    task = await _create_task(client, auth_headers, client_agent, provider_agent)

    # Simulate task completion by directly updating the database
    from sqlalchemy import update
    from uuid import UUID

    stmt = (
        update(Task)
        .where(Task.id == UUID(task["id"]))
        .values(
            status=TaskStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
            credits_charged=10.0,
        )
    )
    await db_session.execute(stmt)
    await db_session.commit()

    # Now rate the task
    resp = await client.post(
        f"/api/v1/tasks/{task['id']}/rate",
        json={"score": 4.5, "comment": "Great work!"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["client_rating"] == 4.5


# ------------------------------------------------------------------
# GET /api/v1/tasks/ -- list tasks with pagination
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_tasks(client: AsyncClient, auth_headers: dict):
    """Listing tasks should return a paginated response."""
    client_agent, provider_agent = await _register_two_agents(client, auth_headers)

    # Create multiple tasks
    for _ in range(3):
        await _create_task(client, auth_headers, client_agent, provider_agent)

    resp = await client.get(
        "/api/v1/tasks/", headers=auth_headers, params={"per_page": 2}
    )
    assert resp.status_code == 200

    body = resp.json()
    assert "tasks" in body
    assert "total" in body
    assert body["total"] >= 3
    # Per-page limit should cap the returned list
    assert len(body["tasks"]) <= 2


# ------------------------------------------------------------------
# x402 payment path tests
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_task_x402_returns_pending_payment(client: AsyncClient, auth_headers: dict):
    """Creating a task with payment_method=x402 should return pending_payment status."""
    client_agent, provider_agent = await _register_two_agents(client, auth_headers)

    # Update provider to accept x402
    resp = await client.put(
        f"/api/v1/agents/{provider_agent['id']}",
        json={"accepted_payment_methods": ["credits", "x402"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    skill_key = provider_agent["skills"][0]["skill_key"]
    task_payload = {
        "provider_agent_id": provider_agent["id"],
        "skill_id": skill_key,
        "messages": [
            {"role": "user", "parts": [{"type": "text", "content": "Analyze this."}]}
        ],
        "max_credits": 10.0,
        "payment_method": "x402",
    }
    resp = await client.post("/api/v1/tasks/", json=task_payload, headers=auth_headers)
    assert resp.status_code == 201

    data = resp.json()
    assert data["status"] == "pending_payment"
    assert data["payment_method"] == "x402"


@pytest.mark.asyncio
async def test_create_task_x402_rejected_if_agent_doesnt_accept(
    client: AsyncClient, auth_headers: dict
):
    """Task creation with x402 should fail if agent only accepts credits."""
    client_agent, provider_agent = await _register_two_agents(client, auth_headers)

    skill_key = provider_agent["skills"][0]["skill_key"]
    task_payload = {
        "provider_agent_id": provider_agent["id"],
        "skill_id": skill_key,
        "messages": [
            {"role": "user", "parts": [{"type": "text", "content": "Analyze this."}]}
        ],
        "max_credits": 10.0,
        "payment_method": "x402",
    }
    resp = await client.post("/api/v1/tasks/", json=task_payload, headers=auth_headers)
    # Should fail because default agent only accepts credits
    assert resp.status_code == 400 or resp.status_code == 500


@pytest.mark.asyncio
async def test_submit_x402_receipt(client: AsyncClient, auth_headers: dict, db_session):
    """Submitting a valid x402 receipt should move task to submitted."""
    client_agent, provider_agent = await _register_two_agents(client, auth_headers)

    # Update provider to accept x402
    await client.put(
        f"/api/v1/agents/{provider_agent['id']}",
        json={"accepted_payment_methods": ["credits", "x402"]},
        headers=auth_headers,
    )

    skill_key = provider_agent["skills"][0]["skill_key"]
    resp = await client.post(
        "/api/v1/tasks/",
        json={
            "provider_agent_id": provider_agent["id"],
            "skill_id": skill_key,
            "messages": [{"role": "user", "parts": [{"type": "text", "content": "Go"}]}],
            "max_credits": 10.0,
            "payment_method": "x402",
        },
        headers=auth_headers,
    )
    task = resp.json()
    assert task["status"] == "pending_payment"

    receipt_resp = await client.post(
        f"/api/v1/tasks/{task['id']}/x402-receipt",
        json={
            "tx_hash": "0xabc123def456",
            "chain": "base",
            "token": "USDC",
            "amount": 10.0,
            "payer": "0xmywallet",
            "payee": "0xproviderwallet",
        },
        headers=auth_headers,
    )
    assert receipt_resp.status_code == 200

    data = receipt_resp.json()
    assert data["verified"] is True
    assert data["task_status"] == "submitted"
