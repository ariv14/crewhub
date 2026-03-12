"""Stripe billing endpoints for credit purchases.

Flow:
  1. POST /billing/credits-checkout → creates Stripe Checkout session for credit packs
  2. Stripe redirects user back after payment
  3. POST /billing/webhook → Stripe webhook fulfils credit purchase
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

class CheckoutResponse(BaseModel):
    checkout_url: str


# ---------------------------------------------------------------------------
# Credit packs (tiered pricing)
# ---------------------------------------------------------------------------

# Default packs when STRIPE_CREDIT_PACKS is not configured
_DEFAULT_PACKS = [
    {"credits": 500, "price_cents": 500, "label": "500 Credits", "savings": None},
    {"credits": 2000, "price_cents": 1800, "label": "2,000 Credits", "savings": "10% off"},
    {"credits": 5000, "price_cents": 4000, "label": "5,000 Credits", "savings": "20% off"},
    {"credits": 10000, "price_cents": 7000, "label": "10,000 Credits", "savings": "30% off"},
]


def _parse_credit_packs() -> dict[int, str]:
    """Parse STRIPE_CREDIT_PACKS env var into {credits: price_id} mapping."""
    if not settings.stripe_credit_packs:
        return {}
    packs = {}
    for pair in settings.stripe_credit_packs.split(","):
        pair = pair.strip()
        if ":" not in pair:
            continue
        credits_str, price_id = pair.split(":", 1)
        packs[int(credits_str)] = price_id
    return packs


class CreditPack(BaseModel):
    credits: int
    price_cents: int
    label: str
    savings: str | None = None


class CreditPacksResponse(BaseModel):
    packs: list[CreditPack]


@router.get("/credit-packs", response_model=CreditPacksResponse)
async def get_credit_packs() -> CreditPacksResponse:
    """Get available credit pack tiers for purchase."""
    return CreditPacksResponse(packs=[CreditPack(**p) for p in _DEFAULT_PACKS])


# ---------------------------------------------------------------------------
# Credits checkout (one-time payment)
# ---------------------------------------------------------------------------


class CreditsCheckoutRequest(BaseModel):
    amount: int  # Number of credits to purchase (must match a pack tier)


@router.post("/credits-checkout", response_model=CheckoutResponse)
async def create_credits_checkout(
    data: CreditsCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> CheckoutResponse:
    """Create a Stripe Checkout session for a one-time credit purchase."""
    stripe = _get_stripe()

    # Validate amount matches a known pack
    valid_amounts = {p["credits"] for p in _DEFAULT_PACKS}
    if data.amount not in valid_amounts:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid credit amount. Choose from: {sorted(valid_amounts)}",
        )

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

    # Use Stripe Price ID if configured, otherwise use dynamic price_data
    price_id_map = _parse_credit_packs()
    price_id = price_id_map.get(data.amount)

    if price_id:
        line_items = [{"price": price_id, "quantity": 1}]
    else:
        # Fallback: dynamic pricing (1 credit = 1 cent)
        pack = next(p for p in _DEFAULT_PACKS if p["credits"] == data.amount)
        line_items = [{
            "price_data": {
                "currency": "usd",
                "unit_amount": pack["price_cents"],
                "product_data": {
                    "name": f"{data.amount} CrewHub Credits",
                    "description": f"One-time purchase of {pack['label']}",
                },
            },
            "quantity": 1,
        }]

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="payment",
        line_items=line_items,
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
# Billing status
# ---------------------------------------------------------------------------


class BillingStatus(BaseModel):
    account_tier: str
    stripe_customer_id: str | None = None


@router.get("/status", response_model=BillingStatus)
async def get_billing_status(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> BillingStatus:
    """Get current user's billing status."""
    user = await _get_user(db, current_user)
    return BillingStatus(
        account_tier=user.account_tier,
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
    """Handle Stripe webhook events.

    Events handled:
      - checkout.session.completed → fulfil credit purchase
      - transfer.paid → mark payout completed
      - transfer.failed → mark payout failed + refund credits
      - account.updated → update Connect onboarding status
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
    elif event_type in ("transfer.paid", "transfer.failed"):
        await _handle_transfer_event(db, event_type, data)
    elif event_type == "account.updated":
        await _handle_account_updated(db, data)
    else:
        logger.debug("Unhandled Stripe event: %s", event_type)

    return {"status": "ok"}


async def _handle_checkout_completed(db: AsyncSession, session: dict) -> None:
    """Handle successful checkout — credit purchase fulfilment."""
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

    if metadata.get("type") != "credits":
        logger.warning("Unknown checkout type: %s", metadata.get("type"))
        return

    credits_amount = int(metadata.get("credits_amount", 0))
    session_id = session.get("id", "")
    if credits_amount <= 0:
        return

    # Idempotency: check if this checkout session was already processed
    from src.models.transaction import Transaction
    existing = await db.execute(
        select(Transaction).where(
            Transaction.description.contains(session_id)
        )
    )
    if existing.scalar_one_or_none():
        logger.info("Duplicate webhook for session %s, skipping", session_id)
        return

    from src.services.credit_ledger import CreditLedgerService
    ledger = CreditLedgerService(db)
    await ledger.purchase_credits(
        owner_id=user.id,
        amount=credits_amount,
        description=f"Credit purchase of {credits_amount} (session: {session_id})",
    )
    logger.info("User %s purchased %d credits via Stripe (session: %s)", user.id, credits_amount, session_id)


async def _handle_transfer_event(db: AsyncSession, event_type: str, transfer: dict) -> None:
    """Handle transfer.paid / transfer.failed for developer payouts."""
    from src.services.payout_service import PayoutService
    service = PayoutService(db)
    await service.handle_transfer_event(event_type, transfer)


async def _handle_account_updated(db: AsyncSession, account_data: dict) -> None:
    """Handle account.updated — sync Connect onboarding status."""
    connect_account_id = account_data.get("id")
    if not connect_account_id:
        return

    result = await db.execute(
        select(User).where(User.stripe_connect_account_id == connect_account_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        logger.debug("No user found for Connect account %s", connect_account_id)
        return

    charges_enabled = account_data.get("charges_enabled", False)
    payouts_enabled = account_data.get("payouts_enabled", False)
    details_submitted = account_data.get("details_submitted", False)

    user.stripe_connect_onboarded = details_submitted
    user.stripe_connect_payouts_enabled = payouts_enabled
    await db.commit()
    logger.info(
        "Connect account %s updated: onboarded=%s payouts_enabled=%s",
        connect_account_id, details_submitted, payouts_enabled,
    )
