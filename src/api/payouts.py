"""Developer payout endpoints — Stripe Connect onboarding and withdrawals."""

import logging
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.auth import get_current_user
from src.database import get_db
from src.schemas.payouts import (
    ConnectStatusResponse,
    OnboardingResponse,
    PayoutEstimateResponse,
    PayoutHistoryResponse,
    PayoutRequestInput,
    PayoutResponse,
    WithdrawableBalanceResponse,
)
from src.services.payout_service import PayoutService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payouts", tags=["payouts"])


def _resolve_user_id(current_user: dict):
    """Extract UUID user ID from auth context."""
    from uuid import UUID
    uid = current_user.get("id")
    if not uid:
        raise HTTPException(status_code=401, detail="User ID not found in token")
    return UUID(uid) if isinstance(uid, str) else uid


@router.post("/connect/onboard", response_model=OnboardingResponse)
async def connect_onboard(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a Stripe Express account and return the onboarding URL."""
    user_id = _resolve_user_id(current_user)
    service = PayoutService(db)
    try:
        url = await service.create_connect_account(user_id)
    except Exception as e:
        logger.error("Connect onboarding failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=str(e))
    return OnboardingResponse(onboarding_url=url)


@router.get("/connect/status", response_model=ConnectStatusResponse)
async def connect_status(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Check the user's Stripe Connect account status."""
    user_id = _resolve_user_id(current_user)
    service = PayoutService(db)
    try:
        status = await service.check_connect_status(user_id)
    except Exception as e:
        logger.error("Connect status check failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=str(e))
    return ConnectStatusResponse(**status)


@router.get("/balance", response_model=WithdrawableBalanceResponse)
async def get_balance(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get withdrawable and pending-clearance balance."""
    user_id = _resolve_user_id(current_user)
    service = PayoutService(db)
    balance = await service.get_withdrawable_balance(user_id)
    return WithdrawableBalanceResponse(**balance)


@router.post("/request", response_model=PayoutResponse)
async def request_payout(
    data: PayoutRequestInput,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Request a payout (minimum 2500 credits / $25)."""
    user_id = _resolve_user_id(current_user)
    service = PayoutService(db)
    try:
        payout = await service.request_payout(user_id, data.amount_credits)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return PayoutResponse.model_validate(payout)


@router.get("/estimate", response_model=PayoutEstimateResponse)
async def estimate_payout(
    amount_credits: float = Query(ge=2500, description="Credits to withdraw"),
):
    """Estimate payout fees for a given credit amount (no auth required for preview)."""
    rate = settings.credit_to_usd_rate
    gross_usd = amount_credits * rate
    gross_usd_cents = int(round(gross_usd * 100))
    stripe_fee_cents = int(math.ceil(gross_usd * 0.0025 * 100 + 25))
    net_usd_cents = gross_usd_cents - stripe_fee_cents
    return PayoutEstimateResponse(
        gross_usd_cents=gross_usd_cents,
        stripe_fee_cents=stripe_fee_cents,
        net_usd_cents=max(0, net_usd_cents),
    )


@router.get("/history", response_model=PayoutHistoryResponse)
async def payout_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get paginated payout history."""
    user_id = _resolve_user_id(current_user)
    service = PayoutService(db)
    payouts, total = await service.get_payout_history(user_id, page, per_page)
    return PayoutHistoryResponse(
        payouts=[PayoutResponse.model_validate(p) for p in payouts],
        total=total,
        page=page,
        per_page=per_page,
    )
