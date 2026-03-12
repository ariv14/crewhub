"""Pydantic schemas for workflows."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.agent import AgentResponse, SkillResponse


# --- Steps ---

class WorkflowStepCreate(BaseModel):
    agent_id: UUID
    skill_id: UUID
    step_group: int = Field(0, ge=0)
    position: int = Field(0, ge=0)
    input_mode: str = Field("chain", pattern=r"^(chain|original|custom)$")
    input_template: Optional[str] = None
    label: Optional[str] = Field(None, max_length=255)
    instructions: Optional[str] = Field(None, max_length=1000)


class WorkflowStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID
    agent_id: UUID
    skill_id: UUID
    step_group: int
    position: int
    input_mode: str
    input_template: Optional[str]
    label: Optional[str]
    instructions: Optional[str]
    agent: AgentResponse
    skill: SkillResponse


# --- Workflow CRUD ---

class WorkflowCreate(BaseModel):
    name: str = Field(max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    icon: str = Field("🔗", max_length=10)
    is_public: bool = False
    max_total_credits: Optional[int] = Field(None, ge=1)
    timeout_seconds: Optional[int] = Field(1800, ge=60, le=7200)
    step_timeout_seconds: Optional[int] = Field(120, ge=30, le=3600)
    steps: list[WorkflowStepCreate] = Field(default=[], max_length=50)


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    icon: Optional[str] = Field(None, max_length=10)
    is_public: Optional[bool] = None
    max_total_credits: Optional[int] = Field(None, ge=0)
    timeout_seconds: Optional[int] = Field(None, ge=60, le=7200)
    step_timeout_seconds: Optional[int] = Field(None, ge=30, le=3600)
    steps: Optional[list[WorkflowStepCreate]] = None


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    name: str
    description: Optional[str]
    icon: str
    is_public: bool
    max_total_credits: Optional[int]
    timeout_seconds: Optional[int]
    step_timeout_seconds: Optional[int]
    steps: list[WorkflowStepResponse]
    created_at: datetime
    updated_at: datetime


class WorkflowListResponse(BaseModel):
    workflows: list[WorkflowResponse]
    total: int


# --- Runs ---

class WorkflowRunRequest(BaseModel):
    message: str = Field(max_length=10000)


class WorkflowStepRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    step_id: Optional[UUID]
    task_id: Optional[UUID]
    step_group: int
    status: str
    output_text: Optional[str]
    error: Optional[str]
    credits_charged: Optional[Decimal]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class WorkflowRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID
    user_id: UUID
    schedule_id: Optional[UUID]
    status: str
    current_step_group: int
    input_message: str
    workflow_snapshot: Optional[dict]
    total_credits_charged: Optional[Decimal]
    error: Optional[str]
    step_runs: list[WorkflowStepRunResponse]
    created_at: datetime
    completed_at: Optional[datetime]


class WorkflowRunListResponse(BaseModel):
    runs: list[WorkflowRunResponse]
    total: int
