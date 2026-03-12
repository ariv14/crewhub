"""End-to-end multi-step flow tests chaining billing, keys, search, and tiers.

These tests exercise realistic user journeys across multiple API endpoints.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import _make_agent_payload, _unique_email


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


async def _register_and_login(client: AsyncClient, name: str = "E2E User"):
    """Register + login, return (headers, user_id, email, password)."""
    email = _unique_email()
    password = "E2eTestPass123"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": name},
    )
    assert reg.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password, "name": name},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = await client.get("/api/v1/auth/me", headers=headers)
    user_id = me.json()["id"]
    return headers, user_id, email, password


# ------------------------------------------------------------------
# 1. Full BYOK flow
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_byok_flow(client: AsyncClient):
    """Register → register agent → set LLM key → discover via keyword."""
    headers, user_id, _, _ = await _register_and_login(client)

    # Register agent first (uses FakeProvider in debug mode)
    agent_resp = await client.post(
        "/api/v1/agents/",
        json=_make_agent_payload(
            name="BYOK Discovery Agent",
            description="Agent for BYOK flow testing",
        ),
        headers=headers,
    )
    assert agent_resp.status_code == 201

    # Set key (for future semantic search)
    key_resp = await client.put(
        "/api/v1/llm-keys/openai",
        json={"provider": "openai", "api_key": "sk-byok-flow-test-key"},
        headers=headers,
    )
    assert key_resp.status_code == 200
    assert key_resp.json()["is_set"] is True

    # Discover via keyword search
    search_resp = await client.post(
        "/api/v1/discover/",
        json={"query": "BYOK", "mode": "keyword"},
        headers=headers,
    )
    assert search_resp.status_code == 200
    names = [m["agent"]["name"] for m in search_resp.json()["matches"]]
    assert "BYOK Discovery Agent" in names


# ------------------------------------------------------------------
# 2. Billing status for new user (subscriptions removed)
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_new_user_billing_status(
    client: AsyncClient,
):
    """New user should have account_tier='free'."""
    headers, user_id, _, _ = await _register_and_login(client)

    status = await client.get("/api/v1/billing/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["account_tier"] == "free"


# ------------------------------------------------------------------
# 3. Onboarding to first task
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_onboarding_to_first_task(client: AsyncClient):
    """Register → complete onboarding → set LLM key → register agent → create task."""
    headers, user_id, _, _ = await _register_and_login(client)

    # Complete onboarding
    onboard = await client.post(
        "/api/v1/auth/onboarding",
        json={"name": "Onboarded User", "interests": ["ai", "automation"]},
        headers=headers,
    )
    assert onboard.status_code == 200

    # Register agent first (uses FakeProvider in debug mode)
    agent_resp = await client.post(
        "/api/v1/agents/",
        json=_make_agent_payload(name="Onboard Agent"),
        headers=headers,
    )
    assert agent_resp.status_code == 201
    agent_id = agent_resp.json()["id"]

    # Set LLM key (after agent registration to avoid real API calls)
    await client.put(
        "/api/v1/llm-keys/openai",
        json={"provider": "openai", "api_key": "sk-onboard-test"},
        headers=headers,
    )

    # Create task for the agent's skill
    skills = agent_resp.json()["skills"]
    if skills:
        task_resp = await client.post(
            "/api/v1/tasks/",
            json={
                "provider_agent_id": agent_id,
                "skill_id": skills[0]["id"],
                "messages": [{"role": "user", "parts": [{"type": "text", "content": "Summarize this"}]}],
            },
            headers=headers,
        )
        assert task_resp.status_code in (200, 201, 402)


# ------------------------------------------------------------------
# 4. Org team task flow
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_org_team_task_flow(client: AsyncClient):
    """Register 2 users → create org → invite second → both see org."""
    headers1, _, _, _ = await _register_and_login(client, name="Org Owner")
    headers2, _, email2, _ = await _register_and_login(client, name="Org Member")

    # Create org
    org_resp = await client.post(
        "/api/v1/organizations/",
        json={"name": "Test Org", "slug": "test-org-e2e"},
        headers=headers1,
    )
    assert org_resp.status_code == 201
    org_id = org_resp.json()["id"]

    # Invite second user
    invite_resp = await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"user_email": email2, "role": "member"},
        headers=headers1,
    )
    assert invite_resp.status_code in (200, 201)

    # Both users can view org
    org_view1 = await client.get(f"/api/v1/organizations/{org_id}", headers=headers1)
    assert org_view1.status_code == 200

    org_view2 = await client.get(f"/api/v1/organizations/{org_id}", headers=headers2)
    assert org_view2.status_code == 200


# ------------------------------------------------------------------
# 5. API key auth flow
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_key_auth_flow(client: AsyncClient):
    """Register → generate API key → use it → revoke → verify rejected."""
    headers, _, _, _ = await _register_and_login(client)

    # Generate API key
    key_resp = await client.post(
        "/api/v1/auth/api-keys",
        json={"name": "e2e-test-key"},
        headers=headers,
    )
    assert key_resp.status_code == 201
    api_key = key_resp.json()["key"]

    # Use API key for auth
    api_key_headers = {"X-API-Key": api_key}
    me_resp = await client.get("/api/v1/auth/me", headers=api_key_headers)
    assert me_resp.status_code == 200

    # Revoke
    revoke_resp = await client.post("/api/v1/auth/revoke-api-key", headers=headers)
    assert revoke_resp.status_code == 200

    # Should be rejected after revocation
    me_resp2 = await client.get("/api/v1/auth/me", headers=api_key_headers)
    assert me_resp2.status_code == 401


# ------------------------------------------------------------------
# 6. Graceful degradation E2E
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_graceful_degradation_e2e(client: AsyncClient):
    """No keys → semantic falls back with hint → set key → semantic works."""
    from src.core.embeddings import MissingAPIKeyError

    headers, _, _, _ = await _register_and_login(client)

    # Register an agent to search for
    await client.post(
        "/api/v1/agents/",
        json=_make_agent_payload(name="Degrade Agent", description="Test degradation flow"),
        headers=headers,
    )

    # Semantic search without key — should degrade (patch to simulate prod)
    with patch(
        "src.core.embeddings.EmbeddingService.generate",
        side_effect=MissingAPIKeyError("openai"),
    ):
        resp1 = await client.post(
            "/api/v1/discover/",
            json={"query": "degradation", "mode": "semantic"},
            headers=headers,
        )
    assert resp1.status_code == 200
    assert resp1.json()["hint"] is not None

    # Now do semantic search without patching — debug mode uses FakeProvider, no hint
    resp2 = await client.post(
        "/api/v1/discover/",
        json={"query": "degradation", "mode": "semantic"},
        headers=headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["hint"] is None


# ------------------------------------------------------------------
# 7. Billing status shows free tier (subscriptions removed)
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_billing_status_stays_free(
    client: AsyncClient,
):
    """After subscription removal, all users should remain free tier."""
    headers, user_id, _, _ = await _register_and_login(client)

    s1 = await client.get("/api/v1/billing/status", headers=headers)
    assert s1.status_code == 200
    assert s1.json()["account_tier"] == "free"
