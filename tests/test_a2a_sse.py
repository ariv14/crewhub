"""Tests for A2A server-side JSON-RPC endpoint and SSE streaming."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_a2a_rejects_unauthenticated(client: AsyncClient):
    """A2A endpoint returns 401 without auth credentials."""
    resp = await client.post(
        "/api/v1/a2a",
        json={
            "jsonrpc": "2.0",
            "method": "tasks/get",
            "params": {"id": "00000000-0000-0000-0000-000000000000"},
            "id": 1,
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_a2a_tasks_get_not_found(client: AsyncClient, auth_headers: dict):
    """tasks/get returns task-not-found error for invalid ID."""
    resp = await client.post(
        "/api/v1/a2a",
        json={
            "jsonrpc": "2.0",
            "method": "tasks/get",
            "params": {"id": "00000000-0000-0000-0000-000000000000"},
            "id": 1,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["error"] is not None
    assert data["error"]["code"] == -32001  # TASK_NOT_FOUND


@pytest.mark.asyncio
async def test_a2a_method_not_found(client: AsyncClient, auth_headers: dict):
    """Unknown method returns method-not-found error."""
    resp = await client.post(
        "/api/v1/a2a",
        json={
            "jsonrpc": "2.0",
            "method": "nonexistent/method",
            "params": {},
            "id": 2,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["error"]["code"] == -32601  # METHOD_NOT_FOUND


@pytest.mark.asyncio
async def test_a2a_tasks_send_missing_params(client: AsyncClient, auth_headers: dict):
    """tasks/send with missing required params returns error."""
    resp = await client.post(
        "/api/v1/a2a",
        json={
            "jsonrpc": "2.0",
            "method": "tasks/send",
            "params": {},
            "id": 3,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["error"] is not None
    assert data["error"]["code"] == -32602  # INVALID_PARAMS


@pytest.mark.asyncio
async def test_a2a_tasks_cancel_not_found(client: AsyncClient, auth_headers: dict):
    """tasks/cancel on nonexistent task returns error."""
    resp = await client.post(
        "/api/v1/a2a",
        json={
            "jsonrpc": "2.0",
            "method": "tasks/cancel",
            "params": {"id": "00000000-0000-0000-0000-000000000000"},
            "id": 4,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["error"] is not None


@pytest.mark.asyncio
async def test_a2a_send_subscribe_returns_sse(client: AsyncClient, auth_headers: dict):
    """tasks/sendSubscribe returns text/event-stream content type."""
    resp = await client.post(
        "/api/v1/a2a",
        json={
            "jsonrpc": "2.0",
            "method": "tasks/sendSubscribe",
            "params": {},
            "id": 5,
        },
        headers=auth_headers,
    )
    # Should return SSE stream (or error within the stream)
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Background A2A dispatch races teardown, causing SQLite table lock", strict=False)
async def test_a2a_full_task_lifecycle(
    client: AsyncClient, auth_headers: dict, registered_agent: dict
):
    """Integration test: create task via A2A, verify via tasks/get."""
    agent_id = registered_agent["id"]
    # Get the first skill ID
    skill_id = registered_agent["skills"][0]["id"]

    # 1. Create task via tasks/send
    send_resp = await client.post(
        "/api/v1/a2a",
        json={
            "jsonrpc": "2.0",
            "method": "tasks/send",
            "params": {
                "provider_agent_id": agent_id,
                "skill_id": skill_id,
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Summarize this document"}],
                },
            },
            "id": 10,
        },
        headers=auth_headers,
    )
    assert send_resp.status_code == 200
    send_data = send_resp.json()
    assert send_data.get("error") is None, f"tasks/send error: {send_data.get('error')}"
    task_id = send_data["result"]["id"]
    assert task_id is not None

    # 2. Query task via tasks/get
    get_resp = await client.post(
        "/api/v1/a2a",
        json={
            "jsonrpc": "2.0",
            "method": "tasks/get",
            "params": {"id": task_id},
            "id": 11,
        },
        headers=auth_headers,
    )
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data.get("error") is None
    assert get_data["result"]["id"] == task_id
    assert get_data["result"]["status"] in ("submitted", "pending_payment", "working")


@pytest.mark.asyncio
async def test_a2a_rejects_ssrf_callback(
    client: AsyncClient, auth_headers: dict, registered_agent: dict
):
    """tasks/send rejects private IP callback URLs (SSRF protection)."""
    agent_id = registered_agent["id"]
    skill_id = registered_agent["skills"][0]["id"]

    resp = await client.post(
        "/api/v1/a2a",
        json={
            "jsonrpc": "2.0",
            "method": "tasks/send",
            "params": {
                "provider_agent_id": agent_id,
                "skill_id": skill_id,
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "test"}],
                },
                "pushNotification": {
                    "url": "http://169.254.169.254/latest/meta-data/",
                },
            },
            "id": 20,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["error"] is not None
    assert "callback URL" in data["error"]["message"].lower() or "private" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_a2a_sse_stream_content(
    client: AsyncClient, auth_headers: dict, registered_agent: dict
):
    """tasks/sendSubscribe returns actual SSE event lines."""
    agent_id = registered_agent["id"]
    skill_id = registered_agent["skills"][0]["id"]

    resp = await client.post(
        "/api/v1/a2a",
        json={
            "jsonrpc": "2.0",
            "method": "tasks/sendSubscribe",
            "params": {
                "provider_agent_id": agent_id,
                "skill_id": skill_id,
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "test stream"}],
                },
            },
            "id": 30,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")

    # Parse the SSE body — should contain at least a data: line
    body = resp.text
    assert "data:" in body
