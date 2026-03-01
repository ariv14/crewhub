"""End-to-end multi-step flow tests chaining billing, keys, search, and tiers.

These tests exercise realistic user journeys across multiple API endpoints.
"""

import json
from unittest.mock import patch, MagicMock
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
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


def _make_webhook_event(event_type: str, data_object: dict) -> dict:
    return {
        "id": "evt_e2e_test",
        "type": event_type,
        "data": {"object": data_object},
    }


def _patch_webhook(event_payload: dict):
    from src.config import settings as _settings

    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event.return_value = event_payload
    mock_stripe.SignatureVerificationError = Exception

    class _Ctx:
        def __enter__(self_):
            self_._original = _settings.stripe_webhook_secret
            _settings.stripe_webhook_secret = "whsec_test_fake"
            self_._patcher = patch("src.api.billing._get_stripe", return_value=mock_stripe)
            self_._patcher.__enter__()
            return self_

        def __exit__(self_, *args):
            self_._patcher.__exit__(*args)
            _settings.stripe_webhook_secret = self_._original

    return _Ctx()


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
# 2. Free → premium upgrade flow
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_free_to_premium_upgrade_flow(
    client: AsyncClient, db_session: AsyncSession
):
    """Register (free) → verify status → simulate webhook upgrade → verify premium."""
    headers, user_id, _, _ = await _register_and_login(client)

    # Check free status
    status = await client.get("/api/v1/billing/status", headers=headers)
    assert status.json()["account_tier"] == "free"

    # Set customer id (required for webhook lookup)
    stmt = update(User).where(User.id == UUID(user_id)).values(
        stripe_customer_id="cus_e2e_upgrade"
    )
    await db_session.execute(stmt)
    await db_session.commit()

    # Simulate webhook
    event = _make_webhook_event("checkout.session.completed", {
        "customer": "cus_e2e_upgrade",
        "subscription": "sub_e2e_123",
        "metadata": {"crewhub_user_id": user_id},
    })
    with _patch_webhook(event):
        resp = await client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event),
            headers={"stripe-signature": "t=1,v1=fake", "content-type": "application/json"},
        )
    assert resp.status_code == 200

    # Verify premium
    status2 = await client.get("/api/v1/billing/status", headers=headers)
    assert status2.json()["account_tier"] == "premium"


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
# 7. Billing status reflects webhook
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_billing_status_reflects_webhook(
    client: AsyncClient, db_session: AsyncSession
):
    """Register → check free → send checkout webhook → check premium."""
    headers, user_id, _, _ = await _register_and_login(client)

    # Confirm free
    s1 = await client.get("/api/v1/billing/status", headers=headers)
    assert s1.json()["account_tier"] == "free"

    # Setup customer
    stmt = update(User).where(User.id == UUID(user_id)).values(
        stripe_customer_id="cus_e2e_reflect"
    )
    await db_session.execute(stmt)
    await db_session.commit()

    # Send webhook
    event = _make_webhook_event("checkout.session.completed", {
        "customer": "cus_e2e_reflect",
        "subscription": "sub_e2e_reflect",
        "metadata": {"crewhub_user_id": user_id},
    })
    with _patch_webhook(event):
        await client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event),
            headers={"stripe-signature": "t=1,v1=fake", "content-type": "application/json"},
        )

    # Confirm premium
    s2 = await client.get("/api/v1/billing/status", headers=headers)
    assert s2.json()["account_tier"] == "premium"
    assert s2.json()["has_subscription"] is True
