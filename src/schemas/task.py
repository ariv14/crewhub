from enum import Enum
from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TaskStatus(str, Enum):
    submitted = "submitted"
    working = "working"
    input_required = "input_required"
    completed = "completed"
    failed = "failed"
    canceled = "canceled"
    rejected = "rejected"


class MessagePart(BaseModel):
    type: str  # text, file, data
    content: Optional[str] = None
    data: Optional[dict] = None
    mime_type: Optional[str] = None


class TaskMessage(BaseModel):
    role: str
    parts: list[MessagePart]


class Artifact(BaseModel):
    name: Optional[str] = None
    parts: list[MessagePart]
    metadata: dict = {}


class TaskCreate(BaseModel):
    provider_agent_id: UUID
    skill_id: str
    messages: list[TaskMessage]
    max_credits: Optional[float] = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_agent_id: Optional[UUID] = None
    provider_agent_id: UUID
    skill_id: str | UUID
    status: TaskStatus
    messages: list[TaskMessage]
    artifacts: list[Artifact]
    credits_quoted: Optional[float] = 0
    credits_charged: Optional[float] = 0
    latency_ms: Optional[int] = None
    client_rating: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class TaskRating(BaseModel):
    score: float = Field(ge=1, le=5)
    comment: str = ""


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int
