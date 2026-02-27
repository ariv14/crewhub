"""Task lifecycle endpoints: creation, messaging, cancellation, and rating."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.database import get_db
from src.schemas.task import (
    TaskCreate,
    TaskListResponse,
    TaskMessage,
    TaskRating,
    TaskResponse,
)
from src.services.task_broker import TaskBrokerService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", response_model=TaskResponse, status_code=201)
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
