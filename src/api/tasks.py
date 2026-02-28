"""Task lifecycle endpoints: creation, messaging, cancellation, and rating."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from src.config import settings as app_settings
from src.core.auth import get_current_user
from src.core.exceptions import PaymentVerificationError
from src.core.rate_limiter import rate_limit_dependency
from src.database import get_db
from src.models.task import TaskStatus as TaskStatusModel
from src.models.transaction import Transaction, TransactionType
from src.schemas.task import (
    TaskCreate,
    TaskListResponse,
    TaskMessage,
    TaskRating,
    TaskResponse,
)
from src.schemas.x402 import X402ReceiptResponse, X402ReceiptSubmit
from src.services.task_broker import TaskBrokerService
from src.services.x402 import X402PaymentService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", response_model=TaskResponse, status_code=201,
               dependencies=[Depends(rate_limit_dependency)])
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> TaskResponse:
    """Create a new task for a provider agent.

    Reserves the estimated credits from the caller's account and dispatches
    the task to the target provider agent via the A2A protocol.
    """
    service = TaskBrokerService(db)
    task = await service.create_task(data=data, user_id=UUID(current_user["id"]))
    return task


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> TaskResponse:
    """Get the current status and details of a task."""
    service = TaskBrokerService(db)
    task = await service.get_task(task_id=task_id, user_id=UUID(current_user["id"]))
    return task


@router.post("/{task_id}/messages", response_model=TaskResponse)
async def send_message(
    task_id: UUID,
    data: TaskMessage,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> TaskResponse:
    """Send a follow-up message to an in-progress task.

    Used when the provider agent requests additional input
    (``input_required`` status).
    """
    service = TaskBrokerService(db)
    task = await service.send_message(
        task_id=task_id,
        message=data,
        user_id=UUID(current_user["id"]),
    )
    return task


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> TaskResponse:
    """Cancel a task that is still in progress.

    Any reserved credits are released back to the caller's account.
    """
    service = TaskBrokerService(db)
    task = await service.cancel_task(task_id=task_id, user_id=UUID(current_user["id"]))
    return task


@router.post("/{task_id}/rate", response_model=TaskResponse)
async def rate_task(
    task_id: UUID,
    data: TaskRating,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> TaskResponse:
    """Rate a completed task.

    Only the task creator can submit a rating. The rating contributes to the
    provider agent's reputation score.
    """
    service = TaskBrokerService(db)
    task = await service.rate_task(
        task_id=task_id,
        user_id=UUID(current_user["id"]),
        rating=data,
    )
    return task


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    agent_id: UUID | None = Query(None, description="Filter by agent ID"),
    status: str | None = Query(None, description="Filter by task status"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> TaskListResponse:
    """List tasks with optional filters.

    Requires authentication. Returns tasks where the current user is
    either the client or the provider agent owner.
    """
    service = TaskBrokerService(db)
    tasks, total = await service.list_tasks(
        user_id=UUID(current_user["id"]),
        agent_id=agent_id,
        status=status,
        page=page,
        per_page=per_page,
    )
    return TaskListResponse(tasks=tasks, total=total)


@router.post("/{task_id}/x402-receipt", response_model=X402ReceiptResponse)
async def submit_x402_receipt(
    task_id: UUID,
    receipt: X402ReceiptSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> X402ReceiptResponse:
    """Submit an x402 payment receipt for a pending_payment task."""
    broker = TaskBrokerService(db)
    task = await broker.get_task(task_id, user_id=UUID(current_user["id"]))

    if task.status != TaskStatusModel.PENDING_PAYMENT:
        raise PaymentVerificationError(
            detail=f"Task is not awaiting payment (status: {task.status.value})"
        )

    if task.payment_method != "x402":
        raise PaymentVerificationError(detail="Task does not use x402 payment method")

    # Check receipt timeout
    from datetime import datetime, timezone
    created = task.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - created).total_seconds() / 60
    if elapsed > app_settings.x402_receipt_timeout_minutes:
        raise PaymentVerificationError(
            detail=f"Receipt submission timeout ({app_settings.x402_receipt_timeout_minutes} min)"
        )

    x402_svc = X402PaymentService(db)

    if await x402_svc.check_replay(receipt.tx_hash):
        raise PaymentVerificationError(detail="Transaction hash already used (replay)")

    required_amount = float(task.credits_quoted or 0)
    errors = x402_svc.validate_receipt(receipt, required_amount=required_amount)
    if errors:
        raise PaymentVerificationError(detail="; ".join(errors))

    verified = await x402_svc.verify_with_facilitator(receipt)
    if not verified:
        raise PaymentVerificationError(detail="Facilitator could not verify payment")

    try:
        await x402_svc.record_receipt(task_id=task.id, receipt=receipt)
    except IntegrityError:
        await db.rollback()
        raise PaymentVerificationError(detail="Transaction hash already used (replay)")

    # Create audit transaction for x402 payment
    audit_txn = Transaction(
        type=TransactionType.X402_PAYMENT,
        amount=Decimal(str(receipt.amount)),
        description=f"x402 payment verified: {receipt.tx_hash}",
    )
    db.add(audit_txn)

    task.status = TaskStatusModel.SUBMITTED
    task.x402_receipt = {
        "tx_hash": receipt.tx_hash,
        "chain": receipt.chain,
        "token": receipt.token,
        "amount": receipt.amount,
        "payer": receipt.payer,
        "payee": receipt.payee,
    }
    await db.commit()

    return X402ReceiptResponse(
        verified=True,
        tx_hash=receipt.tx_hash,
        task_status="submitted",
    )
