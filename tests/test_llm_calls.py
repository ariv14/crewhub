"""Tests for F5: LLM Call Inspector — admin-only log viewer."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.llm_call import LLMCall


async def _insert_llm_call(
    db_session: AsyncSession,
    *,
    agent_id: uuid.UUID | None = None,
    provider: str = "openai",
    model: str = "gpt-4",
    status_code: int = 200,
) -> LLMCall:
    """Insert a test LLM call record directly into the database."""
    call = LLMCall(
        agent_id=agent_id,
        provider=provider,
        model=model,
        request_body={"messages": [{"role": "user", "content": "hello"}]},
        response_body={"choices": [{"message": {"content": "hi"}}]},
        status_code=status_code,
        latency_ms=150,
        tokens_input=10,
        tokens_output=5,
    )
    db_session.add(call)
    await db_session.commit()
    await db_session.refresh(call)
    return call


@pytest.mark.asyncio
async def test_list_llm_calls_admin_only(client: AsyncClient, auth_headers: dict):
    """Non-admin user should get 403."""
    resp = await client.get("/api/v1/admin/llm-calls/", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_llm_calls_empty(client: AsyncClient, admin_headers: dict):
    """Admin with no calls → empty list."""
    resp = await client.get("/api/v1/admin/llm-calls/", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["calls"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_create_and_list_llm_call(
    client: AsyncClient, admin_headers: dict, db_session: AsyncSession
):
    """Insert LLM call via DB, verify it appears in the list."""
    await _insert_llm_call(db_session, provider="anthropic", model="claude-opus")

    resp = await client.get("/api/v1/admin/llm-calls/", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["calls"][0]["provider"] == "anthropic"
    assert data["calls"][0]["model"] == "claude-opus"


@pytest.mark.asyncio
async def test_get_llm_call_detail(
    client: AsyncClient, admin_headers: dict, db_session: AsyncSession
):
    """Insert call, GET by ID, verify full request/response body."""
    call = await _insert_llm_call(db_session)

    resp = await client.get(f"/api/v1/admin/llm-calls/{call.id}", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(call.id)
    assert data["request_body"] is not None
    assert data["response_body"] is not None
    assert data["status_code"] == 200


@pytest.mark.asyncio
async def test_llm_calls_filter_by_agent(
    client: AsyncClient,
    admin_headers: dict,
    auth_headers: dict,
    db_session: AsyncSession,
    registered_agent: dict,
):
    """Insert calls for different agents, filter by agent_id."""
    agent_id = uuid.UUID(registered_agent["id"])

    await _insert_llm_call(db_session, agent_id=agent_id, provider="openai")
    await _insert_llm_call(db_session, agent_id=None, provider="gemini")

    resp = await client.get(
        f"/api/v1/admin/llm-calls/?agent_id={agent_id}", headers=admin_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["calls"][0]["agent_id"] == str(agent_id)
