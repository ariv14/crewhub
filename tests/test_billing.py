"""Tests for Stripe billing endpoints (/api/v1/billing).

Premium subscriptions were removed — billing now handles credit purchases only.
Webhook handler tests use patched signature verification so they run without
Stripe keys.
"""

import json
import os
from unittest.mock import patch, MagicMock
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from tests.conftest import _unique_email


# ------------------------------------------------------------------
# Helper: create a user and return (headers, user_id, email)
# ------------------------------------------------------------------


async def _register_user(client: AsyncClient):
    email = _unique_email()
    password = "BillingTest123"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": "Billing User"},
    )
    assert reg.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password, "name": "Billing User"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = await client.get("/api/v1/auth/me", headers=headers)
    user_id = me.json()["id"]
    return headers, user_id, email


# ------------------------------------------------------------------
# GET /billing/status
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_billing_status_free_user(client: AsyncClient, auth_headers: dict):
    """Free user should show account_tier='free'."""
    resp = await client.get("/api/v1/billing/status", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["account_tier"] == "free"
    assert "stripe_customer_id" in body


# ------------------------------------------------------------------
# Webhook tests — patched signature verification
# ------------------------------------------------------------------


def _make_webhook_event(event_type: str, data_object: dict) -> dict:
    """Construct a minimal Stripe event payload."""
    return {
        "id": "evt_test_123",
        "type": event_type,
        "data": {"object": data_object},
    }


def _patch_webhook_verification(event_payload: dict):
    """Context manager to patch Stripe webhook signature verification."""
    from src.config import settings as _settings

    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event.return_value = event_payload
    mock_stripe.SignatureVerificationError = Exception

    original_secret = _settings.stripe_webhook_secret
    _settings.stripe_webhook_secret = "whsec_test_fake"

    class _Ctx:
        def __enter__(self_):
            self_._patcher = patch("src.api.billing._get_stripe", return_value=mock_stripe)
            self_._patcher.__enter__()
            return self_

        def __exit__(self_, *args):
            self_._patcher.__exit__(*args)
            _settings.stripe_webhook_secret = original_secret

    return _Ctx()


@pytest.mark.asyncio
async def test_webhook_credit_purchase(
    client: AsyncClient, db_session: AsyncSession
):
    """checkout.session.completed with credit metadata should add credits."""
    headers, user_id, email = await _register_user(client)

    # Set stripe_customer_id
    stmt = update(User).where(User.id == UUID(user_id)).values(
        stripe_customer_id="cus_test_credits"
    )
    await db_session.execute(stmt)
    await db_session.commit()

    event = _make_webhook_event("checkout.session.completed", {
        "id": "cs_test_credit_purchase_001",
        "customer": "cus_test_credits",
        "metadata": {
            "crewhub_user_id": user_id,
            "type": "credits",
            "credits_amount": "500",
        },
    })

    with _patch_webhook_verification(event):
        resp = await client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event),
            headers={"stripe-signature": "t=1,v1=fake", "content-type": "application/json"},
        )
    assert resp.status_code == 200

    # Verify credits were added (signup bonus 250 + purchase 500 = 750)
    balance = await client.get("/api/v1/credits/balance", headers=headers)
    assert balance.status_code == 200
    assert balance.json()["balance"] >= 500


@pytest.mark.asyncio
async def test_webhook_unknown_checkout_type(
    client: AsyncClient, db_session: AsyncSession
):
    """checkout.session.completed without credit metadata should log warning and return 200."""
    headers, user_id, _ = await _register_user(client)

    stmt = update(User).where(User.id == UUID(user_id)).values(
        stripe_customer_id="cus_test_unknown"
    )
    await db_session.execute(stmt)
    await db_session.commit()

    event = _make_webhook_event("checkout.session.completed", {
        "customer": "cus_test_unknown",
        "metadata": {"crewhub_user_id": user_id},
    })

    with _patch_webhook_verification(event):
        resp = await client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event),
            headers={"stripe-signature": "t=1,v1=fake", "content-type": "application/json"},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_webhook_invalid_signature(client: AsyncClient):
    """Invalid webhook signature should return 400."""
    try:
        import stripe  # noqa: F401
    except ImportError:
        pytest.skip("Stripe SDK not installed")

    if not os.environ.get("STRIPE_SECRET_KEY"):
        pytest.skip("Needs STRIPE_SECRET_KEY")

    resp = await client.post(
        "/api/v1/billing/webhook",
        content=b'{"bad": "payload"}',
        headers={"stripe-signature": "bad_sig", "content-type": "application/json"},
    )
    assert resp.status_code == 400


# ------------------------------------------------------------------
# Unauthenticated
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_billing_unauthenticated(client: AsyncClient):
    """Billing status should return 401 without auth."""
    assert (await client.get("/api/v1/billing/status")).status_code == 401
