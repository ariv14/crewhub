from enum import Enum
from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TaskStatus(str, Enum):
    submitted = "submitted"
    pending_approval = "pending_approval"
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
    type: str = Field(max_length=50, pattern=r"^[a-z][a-z0-9_]*$")  # text, file, data
    content: Optional[str] = Field(None, max_length=100_000)
    text: Optional[str] = Field(None, max_length=100_000, exclude=True)
    data: Optional[dict] = None
    mime_type: Optional[str] = Field(None, max_length=100)

    @model_validator(mode="before")
    @classmethod
    def _accept_text_field(cls, values):
        """Accept A2A-spec 'text' field as alias for 'content'."""
        if isinstance(values, dict):
            if values.get("text") and not values.get("content"):
                values["content"] = values["text"]
        return values


class TaskMessage(BaseModel):
    role: str = Field(max_length=50, pattern=r"^[a-z][a-z0-9_]*$")
    parts: list[MessagePart] = Field(max_length=100)


class Artifact(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    parts: list[MessagePart] = Field(max_length=100)
    metadata: dict = Field(default_factory=dict, max_length=50)


class TaskCreate(BaseModel):
    provider_agent_id: UUID
    skill_id: str = Field(max_length=255)
    messages: list[TaskMessage] = Field(max_length=50)
    max_credits: Optional[float] = Field(None, ge=0, le=100_000)
    tier: Optional[str] = Field(None, max_length=50, description="Pricing tier name (e.g. 'free', 'pro')")
    payment_method: PaymentMethod = PaymentMethod.credits
    validate_match: bool = Field(False, description="If true, check message-skill alignment and return a warning if mismatched")
    confirmed: bool = Field(False, description="If true, bypass high-cost approval check")
    # Delegation tracking (set by frontend when using auto-delegation)
    parent_task_id: Optional[UUID] = None
    suggested_agent_id: Optional[UUID] = None
    suggestion_confidence: Optional[float] = Field(None, ge=0, le=1)


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_agent_id: Optional[UUID] = None
    provider_agent_id: Optional[UUID] = None
    provider_agent_name: Optional[str] = None
    skill_id: Optional[str | UUID] = None
    skill_name: Optional[str] = None
    status: TaskStatus
    messages: list[TaskMessage]
    artifacts: list[Artifact]
    credits_quoted: Optional[float] = 0
    credits_charged: Optional[float] = 0
    latency_ms: Optional[int] = None
    client_rating: Optional[float] = None
    payment_method: str = "credits"
    x402_receipt: Optional[dict] = None
    status_history: list[dict] = []
    quality_score: Optional[float] = None
    eval_model: Optional[str] = None
    eval_relevance: Optional[float] = None
    eval_completeness: Optional[float] = None
    eval_coherence: Optional[float] = None
    delegation_warning: Optional[str] = None
    delegation_depth: int = 0
    parent_task_id: Optional[UUID] = None
    suggested_agent_id: Optional[UUID] = None
    suggestion_confidence: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class TaskRating(BaseModel):
    score: float = Field(ge=1, le=5)
    comment: str = Field("", max_length=2000)


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int
