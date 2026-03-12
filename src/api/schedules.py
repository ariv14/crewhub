"""Schedule API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import resolve_db_user_id
from src.database import get_db
from src.schemas.schedule import (
    ScheduleCreate,
    ScheduleListResponse,
    ScheduleResponse,
    ScheduleUpdate,
)
from src.services.scheduler import SchedulerService

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("/", response_model=ScheduleListResponse)
async def list_my_schedules(
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(resolve_db_user_id),
) -> ScheduleListResponse:
    service = SchedulerService(db)
    schedules, total = await service.list_my_schedules(owner_id)
    return ScheduleListResponse(schedules=schedules, total=total)


@router.post("/", response_model=ScheduleResponse, status_code=201)
async def create_schedule(
    data: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(resolve_db_user_id),
) -> ScheduleResponse:
    service = SchedulerService(db)
    return await service.create_schedule(owner_id, data)


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(resolve_db_user_id),
) -> ScheduleResponse:
    service = SchedulerService(db)
    schedule = await service.get_schedule(schedule_id)
    if schedule.owner_id != owner_id:
        from src.core.exceptions import ForbiddenError
        raise ForbiddenError("You do not own this schedule")
    return schedule


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: UUID,
    data: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(resolve_db_user_id),
) -> ScheduleResponse:
    service = SchedulerService(db)
    return await service.update_schedule(schedule_id, owner_id, data)


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(resolve_db_user_id),
) -> None:
    service = SchedulerService(db)
    await service.delete_schedule(schedule_id, owner_id)


@router.post("/{schedule_id}/pause", response_model=ScheduleResponse)
async def pause_schedule(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(resolve_db_user_id),
) -> ScheduleResponse:
    service = SchedulerService(db)
    return await service.pause_schedule(schedule_id, owner_id)


@router.post("/{schedule_id}/resume", response_model=ScheduleResponse)
async def resume_schedule(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(resolve_db_user_id),
) -> ScheduleResponse:
    service = SchedulerService(db)
    return await service.resume_schedule(schedule_id, owner_id)
