"""Tests for the agent registry endpoints (POST/GET/PUT/DELETE /api/v1/agents)."""

import pytest
from httpx import AsyncClient

# Re-use the payload builder from conftest so tests are concise.
from tests.conftest import _make_agent_payload


# ------------------------------------------------------------------
# POST /api/v1/agents/ -- register a new agent
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_agent(client: AsyncClient, auth_headers: dict):
    """Registering an agent with valid data should return 201 with id, name, and skills."""
    payload = _make_agent_payload(name="Legal Advisor Agent")
    resp = await client.post("/api/v1/agents/", json=payload, headers=auth_headers)

    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["name"] == "Legal Advisor Agent"
    assert isinstance(data["skills"], list)
    assert len(data["skills"]) >= 1
    assert data["skills"][0]["name"] == "Summarize Text"
    assert data["status"] == "active"
    assert data["category"] == "general"


# ------------------------------------------------------------------
# GET /api/v1/agents/ -- list agents
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_agents(client: AsyncClient, auth_headers: dict):
    """Registering two agents and listing should return both."""
    payload_a = _make_agent_payload(name="Agent Alpha")
    payload_b = _make_agent_payload(name="Agent Beta")

    resp_a = await client.post("/api/v1/agents/", json=payload_a, headers=auth_headers)
    resp_b = await client.post("/api/v1/agents/", json=payload_b, headers=auth_headers)
    assert resp_a.status_code == 201
    assert resp_b.status_code == 201

    list_resp = await client.get("/api/v1/agents/")
    assert list_resp.status_code == 200

    body = list_resp.json()
    assert "agents" in body
    assert body["total"] >= 2
    names = {a["name"] for a in body["agents"]}
    assert "Agent Alpha" in names
    assert "Agent Beta" in names


# ------------------------------------------------------------------
# GET /api/v1/agents/{id} -- get agent details
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_agent(client: AsyncClient, registered_agent: dict):
    """Getting an agent by ID should return matching details."""
    agent_id = registered_agent["id"]
    resp = await client.get(f"/api/v1/agents/{agent_id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == agent_id
    assert data["name"] == registered_agent["name"]
    assert data["endpoint"] == registered_agent["endpoint"]
    assert data["version"] == registered_agent["version"]


# ------------------------------------------------------------------
# PUT /api/v1/agents/{id} -- update agent
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_agent(
    client: AsyncClient, auth_headers: dict, registered_agent: dict
):
    """Updating an agent's name should persist the change."""
    agent_id = registered_agent["id"]
    resp = await client.put(
        f"/api/v1/agents/{agent_id}",
        json={"name": "Updated Agent Name"},
        headers=auth_headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Agent Name"
    assert data["id"] == agent_id


# ------------------------------------------------------------------
# DELETE /api/v1/agents/{id} -- deactivate agent
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deactivate_agent(
    client: AsyncClient, auth_headers: dict, registered_agent: dict
):
    """Deactivating an agent should set its status to inactive."""
    agent_id = registered_agent["id"]
    resp = await client.delete(
        f"/api/v1/agents/{agent_id}",
        headers=auth_headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "inactive"

    # Verify via GET that the agent is now inactive
    get_resp = await client.get(f"/api/v1/agents/{agent_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "inactive"


# ------------------------------------------------------------------
# GET /api/v1/agents/{id}/card -- A2A agent card
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_agent_card(client: AsyncClient, registered_agent: dict):
    """The agent card should follow the A2A spec structure."""
    agent_id = registered_agent["id"]
    resp = await client.get(f"/api/v1/agents/{agent_id}/card")

    assert resp.status_code == 200
    card = resp.json()

    # Required A2A card fields
    assert "name" in card
    assert "description" in card
    assert "url" in card
    assert "version" in card
    assert "capabilities" in card
    assert "skills" in card
    assert "securitySchemes" in card
    assert "defaultInputModes" in card
    assert "defaultOutputModes" in card

    assert card["name"] == registered_agent["name"]
    assert isinstance(card["skills"], list)
    assert len(card["skills"]) >= 1
    assert "id" in card["skills"][0]
    assert "name" in card["skills"][0]


# ------------------------------------------------------------------
# POST /api/v1/agents/ without auth -- should be 401
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_agent_unauthorized(client: AsyncClient):
    """Attempting to register an agent without authentication should return 401."""
    payload = _make_agent_payload()
    resp = await client.post("/api/v1/agents/", json=payload)

    assert resp.status_code == 401
