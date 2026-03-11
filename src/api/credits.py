"""Credit balance, purchasing, transaction history, and usage analytics endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import resolve_db_user_id
from src.database import get_db
from src.schemas.credits import (
    BalanceResponse,
    PurchaseRequest,
    SpendByAgentResponse,
    TransactionListResponse,
    TransactionResponse,
    UsageResponse,
)
from src.services.credit_ledger import CreditLedgerService

router = APIRouter(prefix="/credits", tags=["credits"])


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
) -> BalanceResponse:
    """Check the current credit balance for the authenticated user.

    Returns total balance, reserved amount, available credits, and currency.
    """
    service = CreditLedgerService(db)
    balance = await service.get_balance(owner_id=user_id)
    return balance


@router.post("/purchase", response_model=TransactionResponse, status_code=201)
async def purchase_credits(
    data: PurchaseRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
) -> TransactionResponse:
    """Purchase additional credits.

    Currently disabled until Stripe integration is complete.
    In dev/debug mode, directly adds credits to the account.
    """
    from src.config import settings

    if not settings.debug:
        raise HTTPException(
            status_code=403,
            detail="Credit purchases are disabled until payment integration is complete",
        )

    service = CreditLedgerService(db)
    transaction = await service.purchase_credits(
        owner_id=user_id,
        amount=data.amount,
    )
    return transaction


@router.get("/transactions", response_model=TransactionListResponse)
async def list_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
) -> TransactionListResponse:
    """Get paginated transaction history for the authenticated user.

    Includes purchases, task payments, refunds, bonuses, and platform fees.
    """
    service = CreditLedgerService(db)
    transactions, total = await service.get_transactions(
        owner_id=user_id,
        page=page,
        per_page=per_page,
    )
    return TransactionListResponse(transactions=transactions, total=total)


@router.get("/spend-by-agent", response_model=SpendByAgentResponse)
async def get_spend_by_agent(
    period: str = Query("30d", description="Period: 7d, 30d, 90d", pattern="^(7d|30d|90d)$"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
) -> SpendByAgentResponse:
    """Get credit spend breakdown by agent for the authenticated user."""
    service = CreditLedgerService(db)
    breakdown = await service.get_spend_by_agent(owner_id=user_id, period=period)
    return SpendByAgentResponse(breakdown=breakdown, period=period)


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    period: str = Query("30d", description="Usage period: 7d, 30d, 90d", pattern="^(7d|30d|90d)$"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
) -> UsageResponse:
    """Get credit usage analytics for the authenticated user.

    Summarises total spent, total earned, and task counts over the
    requested period.
    """
    service = CreditLedgerService(db)
    usage = await service.get_usage(
        owner_id=user_id,
        period=period,
    )
    return usage
