"""End-to-end test exercising the full marketplace flow.

This test walks through the entire lifecycle:
    1. Register a user
    2. Check initial credit balance
    3. Register a provider agent with skills
    4. Register a client agent
    5. Discover the provider agent via search
    6. Create a task from client to provider
    7. Verify the task status is submitted
    8. Rate the task (after simulating completion)
    9. Check credit transactions
"""

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_marketplace_flow(client: AsyncClient, db_session):
    """Complete end-to-end marketplace flow test."""

    # ------------------------------------------------------------------
    # Step 1: Register a user
    # ------------------------------------------------------------------
    email = f"e2e-{uuid.uuid4().hex[:8]}@example.com"
    register_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePassword123", "name": "E2E Tester"},
    )
    assert register_resp.status_code == 201, (
        f"User registration failed: {register_resp.text}"
    )
    user = register_resp.json()
    assert user["email"] == email
    assert user["name"] == "E2E Tester"

    # Login to get a token
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123", "name": "E2E Tester"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # ------------------------------------------------------------------
    # Step 2: Check initial credit balance
    # ------------------------------------------------------------------
    balance_resp = await client.get("/api/v1/credits/balance", headers=headers)
    assert balance_resp.status_code == 200
    balance = balance_resp.json()
    assert balance["balance"] >= 100.0, "Expected signup bonus of at least 100 credits"
    assert balance["currency"] == "CREDITS"
    initial_balance = balance["balance"]

    # ------------------------------------------------------------------
    # Step 3: Register a provider agent with skills
    # ------------------------------------------------------------------
    provider_payload = {
        "name": "E2E Translation Provider",
        "description": "Translates text between languages using AI",
        "version": "2.0.0",
        "endpoint": "https://translate-agent.example.com/a2a",
        "capabilities": {"streaming": True, "pushNotifications": False},
        "skills": [
            {
                "skill_key": "translate-text",
                "name": "Translate Text",
                "description": "Translate text from one language to another",
                "input_modes": ["text"],
                "output_modes": ["text"],
                "examples": [
                    {
                        "input": "Hello, world!",
                        "output": "Hola, mundo!",
                        "description": "English to Spanish",
                    }
                ],
                "avg_credits": 5.0,
                "avg_latency_ms": 1500,
            }
        ],
        "security_schemes": [],
        "category": "translation",
        "tags": ["language", "translation", "multilingual"],
        "pricing": {"model": "per_task", "credits": 5.0},
    }
    provider_resp = await client.post(
        "/api/v1/agents/", json=provider_payload, headers=headers
    )
    assert provider_resp.status_code == 201, (
        f"Provider registration failed: {provider_resp.text}"
    )
    provider = provider_resp.json()
    assert provider["name"] == "E2E Translation Provider"
    assert provider["status"] == "active"
    assert len(provider["skills"]) == 1

    # ------------------------------------------------------------------
    # Step 4: Register a client agent
    # ------------------------------------------------------------------
    client_payload = {
        "name": "E2E Client Agent",
        "description": "An orchestrator that delegates translation tasks",
        "version": "1.0.0",
        "endpoint": "https://client-agent.example.com/a2a",
        "capabilities": {},
        "skills": [],
        "security_schemes": [],
        "category": "orchestration",
        "tags": ["client", "orchestrator"],
        "pricing": {"model": "flat", "credits": 0},
    }
    client_resp = await client.post(
        "/api/v1/agents/", json=client_payload, headers=headers
    )
    assert client_resp.status_code == 201, (
        f"Client agent registration failed: {client_resp.text}"
    )
    client_agent = client_resp.json()
    assert client_agent["name"] == "E2E Client Agent"

    # ------------------------------------------------------------------
    # Step 5: Discover the provider agent via search
    # ------------------------------------------------------------------
    search_resp = await client.post(
        "/api/v1/discover/",
        json={"query": "translate", "mode": "keyword"},
    )
    assert search_resp.status_code == 200
    search_results = search_resp.json()
    assert search_results["total_candidates"] >= 1

    found_provider = False
    for match in search_results["matches"]:
        if match["agent"]["id"] == provider["id"]:
            found_provider = True
            assert match["relevance_score"] > 0
            break
    assert found_provider, "Provider agent not found in search results"

    # ------------------------------------------------------------------
    # Step 6: Create a task from client to provider
    # ------------------------------------------------------------------
    task_payload = {
        "provider_agent_id": provider["id"],
        "skill_id": "translate-text",
        "messages": [
            {
                "role": "user",
                "parts": [
                    {
                        "type": "text",
                        "content": "Please translate 'Good morning' to French.",
                    }
                ],
            }
        ],
        "max_credits": 5.0,
    }
    task_resp = await client.post(
        "/api/v1/tasks/", json=task_payload, headers=headers
    )
    assert task_resp.status_code == 201, f"Task creation failed: {task_resp.text}"
    task = task_resp.json()
    assert task["status"] == "submitted"
    assert task["provider_agent_id"] == provider["id"]

    # ------------------------------------------------------------------
    # Step 7: Verify the task status is submitted
    # ------------------------------------------------------------------
    get_task_resp = await client.get(
        f"/api/v1/tasks/{task['id']}", headers=headers
    )
    assert get_task_resp.status_code == 200
    assert get_task_resp.json()["status"] == "submitted"

    # ------------------------------------------------------------------
    # Step 8: Rate the task (after simulating completion)
    # ------------------------------------------------------------------
    from sqlalchemy import update
    from uuid import UUID
    from src.models.task import Task, TaskStatus

    stmt = (
        update(Task)
        .where(Task.id == UUID(task["id"]))
        .values(
            status=TaskStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
            credits_charged=5.0,
        )
    )
    await db_session.execute(stmt)
    await db_session.commit()

    rate_resp = await client.post(
        f"/api/v1/tasks/{task['id']}/rate",
        json={"score": 5.0, "comment": "Perfect translation!"},
        headers=headers,
    )
    assert rate_resp.status_code == 200
    rated_task = rate_resp.json()
    assert rated_task["client_rating"] == 5.0

    # ------------------------------------------------------------------
    # Step 9: Check credit transactions
    # ------------------------------------------------------------------
    txn_resp = await client.get("/api/v1/credits/transactions", headers=headers)
    assert txn_resp.status_code == 200

    txn_body = txn_resp.json()
    assert "transactions" in txn_body
    assert txn_body["total"] >= 1, "Expected at least the signup bonus transaction"

    txn_types = [t["type"] for t in txn_body["transactions"]]
    assert "bonus" in txn_types, "Signup bonus transaction should be present"
