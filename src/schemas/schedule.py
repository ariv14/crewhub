"""Pydantic schemas for schedules."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScheduleCreate(BaseModel):
    name: str = Field(max_length=255)
    schedule_type: str = Field(pattern=r"^(single_task|workflow|crew)$")
    target_id: Optional[UUID] = None
    task_params: Optional[dict] = None
    cron_expression: str = Field(max_length=100)
    timezone: str = Field("UTC", max_length=50)
    input_message: Optional[str] = Field(None, max_length=10000)
    is_active: bool = True
    max_runs: Optional[int] = Field(None, ge=1)
    credit_minimum: int = Field(0, ge=0)


class ScheduleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    cron_expression: Optional[str] = Field(None, max_length=100)
    timezone: Optional[str] = Field(None, max_length=50)
    input_message: Optional[str] = Field(None, max_length=10000)
    is_active: Optional[bool] = None
    max_runs: Optional[int] = Field(None, ge=1)
    credit_minimum: Optional[int] = Field(None, ge=0)
    max_consecutive_failures: Optional[int] = Field(None, ge=1)


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    name: str
    schedule_type: str
    target_id: Optional[UUID]
    task_params: Optional[dict]
    cron_expression: str
    timezone: str
    input_message: Optional[str]
    is_active: bool
    next_run_at: Optional[datetime]
    last_run_at: Optional[datetime]
    run_count: int
    max_runs: Optional[int]
    consecutive_failures: int
    max_consecutive_failures: int
    credit_minimum: int
    created_at: datetime


class ScheduleListResponse(BaseModel):
    schedules: list[ScheduleResponse]
    total: int
