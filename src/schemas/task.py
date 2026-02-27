from enum import Enum
from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TaskStatus(str, Enum):
    submitted = "submitted"
    pending_payment = "pending_payment"
    working = "working"
    input_required = "input_required"
    completed = "completed"
    failed = "failed"
    canceled = "canceled"
    rejected = "rejected"


class PaymentMethod(str, Enum):
    credits = "credits"
    x402 = "x402"


class MessagePart(BaseModel):
    type: str = Field(max_length=50)  # text, file, data
    content: Optional[str] = Field(None, max_length=100_000)
    data: Optional[dict] = None
    mime_type: Optional[str] = Field(None, max_length=100)


class TaskMessage(BaseModel):
    role: str = Field(max_length=50)
    parts: list[MessagePart] = Field(max_length=100)


class Artifact(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    parts: list[MessagePart] = Field(max_length=100)
    metadata: dict = {}


class TaskCreate(BaseModel):
    provider_agent_id: UUID
    skill_id: str = Field(max_length=255)
    messages: list[TaskMessage] = Field(max_length=50)
    max_credits: Optional[float] = Field(None, ge=0, le=100_000)
    tier: Optional[str] = Field(None, max_length=50, description="Pricing tier name (e.g. 'free', 'pro')")
    payment_method: PaymentMethod = PaymentMethod.credits


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
    payment_method: str = "credits"
    x402_receipt: Optional[dict] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class TaskRating(BaseModel):
    score: float = Field(ge=1, le=5)
    comment: str = ""


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int
