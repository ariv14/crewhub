"""Pydantic schemas for developer payout endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OnboardingResponse(BaseModel):
    onboarding_url: str


class ConnectStatusResponse(BaseModel):
    connected: bool
    onboarded: bool
    payouts_enabled: bool
    account_id: str | None = None


class WithdrawableBalanceResponse(BaseModel):
    withdrawable_credits: float
    withdrawable_usd_cents: int
    pending_clearance_credits: float
    total_earned_credits: float
    total_paid_out_credits: float
    minimum_payout_credits: float
    credit_to_usd_rate: float


class PayoutRequestInput(BaseModel):
    amount_credits: float = Field(ge=2500, description="Credits to withdraw (min 2500)")


class PayoutEstimateResponse(BaseModel):
    gross_usd_cents: int
    stripe_fee_cents: int
    net_usd_cents: int


class PayoutResponse(BaseModel):
    id: UUID
    amount_credits: float
    amount_usd_cents: int
    stripe_fee_cents: int
    status: str
    stripe_transfer_id: str | None = None
    failure_reason: str | None = None
    requested_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class PayoutHistoryResponse(BaseModel):
    payouts: list[PayoutResponse]
    total: int
    page: int
    per_page: int
