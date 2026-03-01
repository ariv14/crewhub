"""Admin-only endpoints for platform governance.

All endpoints require authentication and is_admin=True on the user record.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.database import get_db
from src.models.agent import Agent
from src.models.task import Task
from src.models.transaction import Transaction
from src.models.user import User
from src.schemas.agent import AgentResponse, AgentStatus
from src.schemas.auth import UserResponse
from src.schemas.task import TaskResponse, TaskListResponse
from src.schemas.credits import TransactionListResponse, TransactionResponse

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Admin guard dependency
# ---------------------------------------------------------------------------


async def require_admin(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency that verifies the current user is an admin."""
    firebase_uid = current_user.get("firebase_uid")
    if firebase_uid:
        result = await db.execute(
            select(User).where(User.firebase_uid == firebase_uid)
        )
    else:
        result = await db.execute(
            select(User).where(User.id == UUID(current_user["id"]))
        )

    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ---------------------------------------------------------------------------
# Platform stats
# ---------------------------------------------------------------------------


class PlatformStats(BaseModel):
    total_users: int
    active_users: int
    total_agents: int
    active_agents: int
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    total_transaction_volume: float


@router.get("/stats", response_model=PlatformStats)
async def get_platform_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> PlatformStats:
    """Aggregated platform KPIs."""
    total_users = (await db.execute(select(func.count(User.id)))).scalar_one()
    active_users = (
        await db.execute(select(func.count(User.id)).where(User.is_active.is_(True)))
    ).scalar_one()

    total_agents = (await db.execute(select(func.count(Agent.id)))).scalar_one()
    active_agents = (
        await db.execute(
            select(func.count(Agent.id)).where(Agent.status == "active")
        )
    ).scalar_one()

    total_tasks = (await db.execute(select(func.count(Task.id)))).scalar_one()
    completed_tasks = (
        await db.execute(
            select(func.count(Task.id)).where(Task.status == "completed")
        )
    ).scalar_one()
    failed_tasks = (
        await db.execute(
            select(func.count(Task.id)).where(Task.status == "failed")
        )
    ).scalar_one()

    vol_result = await db.execute(select(func.coalesce(func.sum(Transaction.amount), 0)))
    total_volume = float(vol_result.scalar_one())

    return PlatformStats(
        total_users=total_users,
        active_users=active_users,
        total_agents=total_agents,
        active_agents=active_agents,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        failed_tasks=failed_tasks,
        total_transaction_volume=total_volume,
    )


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------


class AdminUserListResponse(BaseModel):
    users: list[UserResponse]
    total: int


@router.get("/users/", response_model=AdminUserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUserListResponse:
    """List all platform users (admin only)."""
    total = (await db.execute(select(func.count(User.id)))).scalar_one()
    offset = (page - 1) * per_page
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(offset).limit(per_page)
    )
    users = [UserResponse.model_validate(u) for u in result.scalars().all()]
    return AdminUserListResponse(users=users, total=total)


class UserStatusUpdate(BaseModel):
    is_active: bool | None = None
    is_admin: bool | None = None
    account_tier: str | None = None  # "free" or "premium"


@router.put("/users/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    user_id: UUID,
    data: UserStatusUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Activate/deactivate a user, grant/revoke admin, or set account tier (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.is_admin is not None:
        user.is_admin = data.is_admin
    if data.account_tier is not None:
        if data.account_tier not in ("free", "premium"):
            raise HTTPException(status_code=400, detail="account_tier must be 'free' or 'premium'")
        user.account_tier = data.account_tier
    await db.flush()
    return UserResponse.model_validate(user)


# ---------------------------------------------------------------------------
# All tasks (not user-scoped)
# ---------------------------------------------------------------------------


@router.get("/tasks/", response_model=TaskListResponse)
async def list_all_tasks(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> TaskListResponse:
    """List all tasks across the platform (admin only)."""
    query = select(Task)
    if status:
        query = query.where(Task.status == status)

    total = (
        await db.execute(select(func.count()).select_from(query.subquery()))
    ).scalar_one()

    offset = (page - 1) * per_page
    result = await db.execute(
        query.order_by(Task.created_at.desc()).offset(offset).limit(per_page)
    )
    tasks = [TaskResponse.model_validate(t) for t in result.scalars().all()]
    return TaskListResponse(tasks=tasks, total=total)


# ---------------------------------------------------------------------------
# All transactions
# ---------------------------------------------------------------------------


@router.get("/transactions/", response_model=TransactionListResponse)
async def list_all_transactions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    type: str | None = Query(None, description="Filter by transaction type"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> TransactionListResponse:
    """List all transactions across the platform (admin only)."""
    query = select(Transaction)
    if type:
        query = query.where(Transaction.type == type)

    total = (
        await db.execute(select(func.count()).select_from(query.subquery()))
    ).scalar_one()

    offset = (page - 1) * per_page
    result = await db.execute(
        query.order_by(Transaction.created_at.desc()).offset(offset).limit(per_page)
    )
    txns = [TransactionResponse.model_validate(t) for t in result.scalars().all()]
    return TransactionListResponse(transactions=txns, total=total)


# ---------------------------------------------------------------------------
# Agent admin control
# ---------------------------------------------------------------------------


class AgentStatusUpdate(BaseModel):
    status: AgentStatus


@router.put("/agents/{agent_id}/status", response_model=AgentResponse)
async def update_agent_status(
    agent_id: UUID,
    data: AgentStatusUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Override agent status (suspend/activate) — admin only."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.status = data.status.value
    await db.flush()
    return AgentResponse.model_validate(agent)
