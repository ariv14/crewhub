"""Tests for the credit system endpoints (/api/v1/credits)."""

import pytest
from httpx import AsyncClient

from tests.conftest import _make_agent_payload


# ------------------------------------------------------------------
# GET /api/v1/credits/balance -- check initial balance
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_initial_balance(client: AsyncClient, auth_headers: dict):
    """A newly registered user should receive a default signup bonus of 100 credits."""
    resp = await client.get("/api/v1/credits/balance", headers=auth_headers)
    assert resp.status_code == 200

    data = resp.json()
    assert "balance" in data
    assert "reserved" in data
    assert "available" in data
    assert "currency" in data

    # The default signup bonus defined in settings and applied at registration
    assert data["balance"] >= 100.0
    assert data["currency"] == "CREDITS"
    assert data["available"] >= 100.0


# ------------------------------------------------------------------
# POST /api/v1/credits/purchase -- purchase credits
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_purchase_credits(client: AsyncClient, auth_headers: dict):
    """Purchasing credits should increase the account balance."""
    # Get initial balance
    bal_before = await client.get("/api/v1/credits/balance", headers=auth_headers)
    initial_balance = bal_before.json()["balance"]

    # Purchase 50 credits
    purchase_resp = await client.post(
        "/api/v1/credits/purchase",
        json={"amount": 50.0},
        headers=auth_headers,
    )
    assert purchase_resp.status_code == 201

    data = purchase_resp.json()
    assert "id" in data
    assert data["amount"] == 50.0
    assert data["type"] == "purchase"

    # Verify balance increased
    bal_after = await client.get("/api/v1/credits/balance", headers=auth_headers)
    assert bal_after.json()["balance"] == pytest.approx(initial_balance + 50.0, abs=0.01)


# ------------------------------------------------------------------
# GET /api/v1/credits/transactions -- transaction history
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_transaction_history(client: AsyncClient, auth_headers: dict):
    """After purchasing credits, the transaction history should contain at least
    the signup bonus and the purchase record.
    """
    # Purchase some credits first
    await client.post(
        "/api/v1/credits/purchase",
        json={"amount": 25.0},
        headers=auth_headers,
    )

    resp = await client.get("/api/v1/credits/transactions", headers=auth_headers)
    assert resp.status_code == 200

    body = resp.json()
    assert "transactions" in body
    assert "total" in body
    assert body["total"] >= 1

    txn_types = [t["type"] for t in body["transactions"]]
    assert "purchase" in txn_types


# ------------------------------------------------------------------
# Task creation with insufficient credits -- expect 402
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_insufficient_credits(client: AsyncClient, auth_headers: dict):
    """Trying to create a task costing more than the available balance should return 402."""
    # Register two agents
    client_payload = _make_agent_payload(name="Poor Client Agent")
    provider_payload = _make_agent_payload(
        name="Expensive Provider Agent",
        pricing={"model": "per_task", "credits": 99999.0},
        skills=[
            {
                "skill_key": "expensive-op",
                "name": "Expensive Operation",
                "description": "Costs a lot of credits",
                "input_modes": ["text"],
                "output_modes": ["text"],
                "examples": [],
                "avg_credits": 99999.0,
                "avg_latency_ms": 1000,
            }
        ],
    )

    await client.post("/api/v1/agents/", json=client_payload, headers=auth_headers)
    provider_resp = await client.post(
        "/api/v1/agents/", json=provider_payload, headers=auth_headers
    )
    provider = provider_resp.json()

    # Attempt to create a task with max_credits exceeding balance
    task_payload = {
        "provider_agent_id": provider["id"],
        "skill_id": "expensive-op",
        "messages": [
            {
                "role": "user",
                "parts": [{"type": "text", "content": "Do the expensive thing."}],
            }
        ],
        "max_credits": 99999.0,
    }

    resp = await client.post(
        "/api/v1/tasks/", json=task_payload, headers=auth_headers
    )
    assert resp.status_code == 402


# ------------------------------------------------------------------
# GET /api/v1/credits/usage -- usage analytics
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_usage_analytics(client: AsyncClient, auth_headers: dict):
    """The usage analytics endpoint should return the expected structure."""
    resp = await client.get(
        "/api/v1/credits/usage",
        headers=auth_headers,
        params={"period": "30d"},
    )
    assert resp.status_code == 200

    data = resp.json()
    assert "total_spent" in data
    assert "total_earned" in data
    assert "tasks_created" in data
    assert "tasks_received" in data
    assert "period" in data
    assert data["period"] == "30d"
    assert isinstance(data["total_spent"], (int, float))
    assert isinstance(data["total_earned"], (int, float))
