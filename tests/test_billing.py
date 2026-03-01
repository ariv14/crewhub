"""Tests for Stripe billing endpoints (/api/v1/billing).

Tests marked @stripe_configured require STRIPE_SECRET_KEY env var.
Webhook handler tests use patched signature verification so they run without
Stripe keys.
"""

import json
import os
from unittest.mock import patch, MagicMock
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from tests.conftest import stripe_configured, _unique_email


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
    """Free user should show account_tier='free' and has_subscription=False."""
    resp = await client.get("/api/v1/billing/status", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["account_tier"] == "free"
    assert body["has_subscription"] is False


# ------------------------------------------------------------------
# POST /billing/checkout — requires Stripe
# ------------------------------------------------------------------


@stripe_configured
@pytest.mark.asyncio
async def test_checkout_creates_session(client: AsyncClient, auth_headers: dict):
    """POST /billing/checkout should return a checkout URL."""
    resp = await client.post("/api/v1/billing/checkout", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "checkout_url" in body
    assert "checkout.stripe.com" in body["checkout_url"]


@pytest.mark.asyncio
async def test_checkout_already_premium_rejected(
    client: AsyncClient, premium_user_headers: dict
):
    """Premium user trying to checkout should get 400."""
    # Need stripe to be available for the 400 check to reach
    # If stripe isn't configured, the endpoint returns 503 first
    if not os.environ.get("STRIPE_SECRET_KEY"):
        pytest.skip("Needs STRIPE_SECRET_KEY to reach the 400 path")
    resp = await client.post("/api/v1/billing/checkout", headers=premium_user_headers)
    assert resp.status_code == 400
    assert "premium" in resp.json()["detail"].lower()


# ------------------------------------------------------------------
# POST /billing/portal — requires Stripe
# ------------------------------------------------------------------


@stripe_configured
@pytest.mark.asyncio
async def test_portal_creates_session(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    """POST /billing/portal should return a portal URL for users with a customer ID."""
    # Set a stripe_customer_id in DB
    me = await client.get("/api/v1/auth/me", headers=auth_headers)
    user_id = me.json()["id"]
    stmt = update(User).where(User.id == UUID(user_id)).values(
        stripe_customer_id="cus_test_portal_12345"
    )
    await db_session.execute(stmt)
    await db_session.commit()

    resp = await client.post("/api/v1/billing/portal", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "portal_url" in body


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
    """Context manager to patch Stripe webhook signature verification.

    Patches both _get_stripe and ensures stripe_webhook_secret is set.
    """
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
async def test_webhook_checkout_completed(
    client: AsyncClient, db_session: AsyncSession
):
    """checkout.session.completed should upgrade user to premium."""
    headers, user_id, email = await _register_user(client)

    # Set stripe_customer_id
    stmt = update(User).where(User.id == UUID(user_id)).values(
        stripe_customer_id="cus_test_checkout"
    )
    await db_session.execute(stmt)
    await db_session.commit()

    event = _make_webhook_event("checkout.session.completed", {
        "customer": "cus_test_checkout",
        "subscription": "sub_test_123",
        "metadata": {"crewhub_user_id": user_id},
    })

    with _patch_webhook_verification(event):
        resp = await client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event),
            headers={"stripe-signature": "t=1,v1=fake", "content-type": "application/json"},
        )
    assert resp.status_code == 200

    # Verify tier changed
    db_session.expire_all()
    result = await db_session.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one()
    assert user.account_tier == "premium"


@pytest.mark.asyncio
async def test_webhook_subscription_deleted(
    client: AsyncClient, db_session: AsyncSession
):
    """customer.subscription.deleted should revert user to free."""
    headers, user_id, email = await _register_user(client)

    stmt = update(User).where(User.id == UUID(user_id)).values(
        stripe_customer_id="cus_test_cancel",
        account_tier="premium",
        stripe_subscription_id="sub_cancel",
    )
    await db_session.execute(stmt)
    await db_session.commit()

    event = _make_webhook_event("customer.subscription.deleted", {
        "customer": "cus_test_cancel",
    })

    with _patch_webhook_verification(event):
        resp = await client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event),
            headers={"stripe-signature": "t=1,v1=fake", "content-type": "application/json"},
        )
    assert resp.status_code == 200

    db_session.expire_all()
    result = await db_session.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one()
    assert user.account_tier == "free"
    assert user.stripe_subscription_id is None


@pytest.mark.asyncio
async def test_webhook_subscription_updated_active(
    client: AsyncClient, db_session: AsyncSession
):
    """subscription.updated with status=active should set premium."""
    headers, user_id, _ = await _register_user(client)

    stmt = update(User).where(User.id == UUID(user_id)).values(
        stripe_customer_id="cus_test_update_active",
        account_tier="free",
    )
    await db_session.execute(stmt)
    await db_session.commit()

    event = _make_webhook_event("customer.subscription.updated", {
        "customer": "cus_test_update_active",
        "status": "active",
    })

    with _patch_webhook_verification(event):
        resp = await client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event),
            headers={"stripe-signature": "t=1,v1=fake", "content-type": "application/json"},
        )
    assert resp.status_code == 200

    db_session.expire_all()
    result = await db_session.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one()
    assert user.account_tier == "premium"


@pytest.mark.asyncio
async def test_webhook_subscription_updated_canceled(
    client: AsyncClient, db_session: AsyncSession
):
    """subscription.updated with status=canceled should revert to free."""
    headers, user_id, _ = await _register_user(client)

    stmt = update(User).where(User.id == UUID(user_id)).values(
        stripe_customer_id="cus_test_update_cancel",
        account_tier="premium",
    )
    await db_session.execute(stmt)
    await db_session.commit()

    event = _make_webhook_event("customer.subscription.updated", {
        "customer": "cus_test_update_cancel",
        "status": "canceled",
    })

    with _patch_webhook_verification(event):
        resp = await client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event),
            headers={"stripe-signature": "t=1,v1=fake", "content-type": "application/json"},
        )
    assert resp.status_code == 200

    db_session.expire_all()
    result = await db_session.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one()
    assert user.account_tier == "free"


@pytest.mark.asyncio
async def test_webhook_invalid_signature(client: AsyncClient):
    """Invalid webhook signature should return 400."""
    # Without patching, stripe.Webhook.construct_event will fail on bad sig.
    # But we need stripe to be importable. If not, we get 503.
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


@pytest.mark.asyncio
async def test_webhook_invoice_payment_failed(
    client: AsyncClient, db_session: AsyncSession
):
    """invoice.payment_failed should return 200 without downgrading."""
    headers, user_id, _ = await _register_user(client)

    stmt = update(User).where(User.id == UUID(user_id)).values(
        stripe_customer_id="cus_test_pay_fail",
        account_tier="premium",
    )
    await db_session.execute(stmt)
    await db_session.commit()

    event = _make_webhook_event("invoice.payment_failed", {
        "customer": "cus_test_pay_fail",
    })

    with _patch_webhook_verification(event):
        resp = await client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event),
            headers={"stripe-signature": "t=1,v1=fake", "content-type": "application/json"},
        )
    assert resp.status_code == 200

    # User should still be premium (no immediate downgrade)
    db_session.expire_all()
    result = await db_session.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one()
    assert user.account_tier == "premium"


# ------------------------------------------------------------------
# No Stripe config
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_billing_no_stripe_config(client: AsyncClient, auth_headers: dict):
    """Without stripe key configured, checkout should return 503."""
    from src.config import settings

    original = settings.stripe_secret_key
    try:
        settings.stripe_secret_key = ""
        resp = await client.post("/api/v1/billing/checkout", headers=auth_headers)
        assert resp.status_code == 503
    finally:
        settings.stripe_secret_key = original


# ------------------------------------------------------------------
# Unauthenticated
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_billing_unauthenticated(client: AsyncClient):
    """All billing endpoints should return 401 without auth."""
    assert (await client.get("/api/v1/billing/status")).status_code == 401
    assert (await client.post("/api/v1/billing/checkout")).status_code == 401
    assert (await client.post("/api/v1/billing/portal")).status_code == 401
