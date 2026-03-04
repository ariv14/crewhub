"""Stripe billing endpoints for self-serve premium tier upgrade.

Flow:
  1. POST /billing/checkout → creates Stripe Checkout session, returns URL
  2. Stripe redirects user back after payment
  3. POST /billing/webhook → Stripe webhook updates account_tier
  4. POST /billing/portal → creates Stripe Billing Portal session for management
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.auth import get_current_user
from src.database import get_db
from src.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])


def _get_stripe():
    """Lazy-import stripe to avoid ImportError if not installed."""
    try:
        import stripe
        if not settings.stripe_secret_key:
            raise HTTPException(status_code=503, detail="Stripe is not configured")
        stripe.api_key = settings.stripe_secret_key
        return stripe
    except ImportError:
        raise HTTPException(status_code=503, detail="Stripe SDK not installed")


async def _get_user(
    db: AsyncSession, current_user: dict, *, for_update: bool = False
) -> User:
    firebase_uid = current_user.get("firebase_uid")
    if firebase_uid:
        stmt = select(User).where(User.firebase_uid == firebase_uid)
    else:
        stmt = select(User).where(User.id == UUID(current_user["id"]))
    if for_update:
        stmt = stmt.with_for_update()
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ---------------------------------------------------------------------------
# Create checkout session
# ---------------------------------------------------------------------------


class CheckoutResponse(BaseModel):
    checkout_url: str


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> CheckoutResponse:
    """Create a Stripe Checkout session for premium subscription ($9/mo)."""
    stripe = _get_stripe()
    user = await _get_user(db, current_user, for_update=True)

    if user.account_tier == "premium":
        raise HTTPException(status_code=400, detail="Already on premium tier")

    # Reuse existing Stripe customer or create new one
    customer_id = user.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            name=user.name,
            metadata={"crewhub_user_id": str(user.id)},
        )
        customer_id = customer.id
        user.stripe_customer_id = customer_id
        await db.commit()

    # Build checkout session
    checkout_params = {
        "customer": customer_id,
        "mode": "subscription",
        "success_url": f"{settings.frontend_url}/dashboard/settings?upgrade=success",
        "cancel_url": f"{settings.frontend_url}/dashboard/settings?upgrade=cancelled",
        "metadata": {"crewhub_user_id": str(user.id)},
    }

    # Use existing Stripe Price ID or create line item with price_data
    if settings.stripe_price_id:
        checkout_params["line_items"] = [{"price": settings.stripe_price_id, "quantity": 1}]
    else:
        checkout_params["line_items"] = [{
            "price_data": {
                "currency": "usd",
                "unit_amount": settings.premium_monthly_price,
                "recurring": {"interval": "month"},
                "product_data": {
                    "name": "CrewHub Premium",
                    "description": "Unlimited API calls, no rate limits",
                },
            },
            "quantity": 1,
        }]

    session = stripe.checkout.Session.create(**checkout_params)
    return CheckoutResponse(checkout_url=session.url)


# ---------------------------------------------------------------------------
# Credits checkout (one-time payment)
# ---------------------------------------------------------------------------


class CreditsCheckoutRequest(BaseModel):
    amount: int  # Number of credits to purchase (minimum 100)


@router.post("/credits-checkout", response_model=CheckoutResponse)
async def create_credits_checkout(
    data: CreditsCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> CheckoutResponse:
    """Create a Stripe Checkout session for a one-time credit purchase."""
    stripe = _get_stripe()

    if data.amount < 100:
        raise HTTPException(status_code=400, detail="Minimum purchase is 100 credits")

    user = await _get_user(db, current_user, for_update=True)

    # Reuse existing Stripe customer or create new one
    customer_id = user.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            name=user.name,
            metadata={"crewhub_user_id": str(user.id)},
        )
        customer_id = customer.id
        user.stripe_customer_id = customer_id
        await db.commit()

    # $1 per 100 credits (1 cent per credit)
    unit_amount = data.amount  # 1 credit = 1 cent

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "usd",
                "unit_amount": unit_amount,
                "product_data": {
                    "name": f"{data.amount} CrewHub Credits",
                    "description": f"One-time purchase of {data.amount} credits",
                },
            },
            "quantity": 1,
        }],
        success_url=f"{settings.frontend_url}/dashboard/credits?purchase=success",
        cancel_url=f"{settings.frontend_url}/dashboard/credits?purchase=cancelled",
        metadata={
            "crewhub_user_id": str(user.id),
            "type": "credits",
            "credits_amount": str(data.amount),
        },
    )
    return CheckoutResponse(checkout_url=session.url)


# ---------------------------------------------------------------------------
# Billing portal (manage/cancel subscription)
# ---------------------------------------------------------------------------


class PortalResponse(BaseModel):
    portal_url: str


@router.post("/portal", response_model=PortalResponse)
async def create_portal_session(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> PortalResponse:
    """Create a Stripe Billing Portal session for subscription management."""
    stripe = _get_stripe()
    user = await _get_user(db, current_user)

    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account found")

    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{settings.frontend_url}/dashboard/settings",
    )
    return PortalResponse(portal_url=session.url)


# ---------------------------------------------------------------------------
# Subscription status
# ---------------------------------------------------------------------------


class SubscriptionStatus(BaseModel):
    account_tier: str
    has_subscription: bool
    stripe_customer_id: str | None = None


@router.get("/status", response_model=SubscriptionStatus)
async def get_subscription_status(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> SubscriptionStatus:
    """Get current user's subscription status."""
    user = await _get_user(db, current_user)
    return SubscriptionStatus(
        account_tier=user.account_tier,
        has_subscription=bool(user.stripe_subscription_id),
        stripe_customer_id=user.stripe_customer_id,
    )


# ---------------------------------------------------------------------------
# Stripe webhook
# ---------------------------------------------------------------------------


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle Stripe webhook events for subscription lifecycle.

    Events handled:
      - checkout.session.completed → activate premium
      - customer.subscription.deleted → revert to free
      - customer.subscription.updated → handle plan changes
      - invoice.payment_failed → revert to free (grace period could be added)
    """
    stripe = _get_stripe()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(db, data)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_cancelled(db, data)
    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(db, data)
    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(db, data)
    else:
        logger.debug("Unhandled Stripe event: %s", event_type)

    return {"status": "ok"}


async def _handle_checkout_completed(db: AsyncSession, session: dict) -> None:
    """Handle successful checkout — premium subscription or credit purchase."""
    metadata = session.get("metadata") or {}
    customer_id = session.get("customer")

    if not customer_id:
        logger.warning("Checkout completed without customer ID")
        return

    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        # Try metadata fallback
        user_id = metadata.get("crewhub_user_id")
        if user_id:
            result = await db.execute(select(User).where(User.id == UUID(user_id)))
            user = result.scalar_one_or_none()

    if not user:
        logger.error("Could not find user for Stripe customer %s", customer_id)
        return

    # Credit purchase (one-time payment)
    if metadata.get("type") == "credits":
        credits_amount = int(metadata.get("credits_amount", 0))
        if credits_amount > 0:
            from src.services.credit_ledger import CreditLedgerService
            ledger = CreditLedgerService(db)
            await ledger.purchase_credits(owner_id=user.id, amount=credits_amount)
            logger.info("User %s purchased %d credits via Stripe", user.id, credits_amount)
        return

    # Subscription upgrade
    subscription_id = session.get("subscription")
    user.account_tier = "premium"
    user.stripe_customer_id = customer_id
    if subscription_id:
        user.stripe_subscription_id = subscription_id
    await db.commit()
    logger.info("User %s upgraded to premium", user.id)


async def _handle_subscription_cancelled(db: AsyncSession, subscription: dict) -> None:
    """Revert to free tier when subscription is cancelled."""
    customer_id = subscription.get("customer")
    if not customer_id:
        return

    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    user.account_tier = "free"
    user.stripe_subscription_id = None
    await db.commit()
    logger.info("User %s downgraded to free (subscription cancelled)", user.id)


async def _handle_subscription_updated(db: AsyncSession, subscription: dict) -> None:
    """Handle subscription status changes (e.g., past_due, active)."""
    customer_id = subscription.get("customer")
    status = subscription.get("status")
    if not customer_id:
        return

    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    if status in ("active", "trialing"):
        user.account_tier = "premium"
    elif status in ("past_due", "unpaid", "canceled", "incomplete_expired"):
        user.account_tier = "free"
        user.stripe_subscription_id = None

    await db.commit()
    logger.info("User %s subscription updated: status=%s tier=%s", user.id, status, user.account_tier)


async def _handle_payment_failed(db: AsyncSession, invoice: dict) -> None:
    """Handle failed payment — could add grace period logic here."""
    customer_id = invoice.get("customer")
    if not customer_id:
        return

    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    logger.warning("Payment failed for user %s (customer %s)", user.id, customer_id)
    # NOTE: Don't immediately downgrade — Stripe retries. Downgrade on subscription.deleted.
