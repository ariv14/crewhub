import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class TaskStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    PENDING_APPROVAL = "pending_approval"
    PENDING_PAYMENT = "pending_payment"
    WORKING = "working"
    INPUT_REQUIRED = "input_required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    REJECTED = "rejected"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    creator_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    client_agent_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    provider_agent_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    skill_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("agent_skills.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[TaskStatus] = mapped_column(
        String(20), nullable=False, default=TaskStatus.SUBMITTED, index=True
    )
    messages: Mapped[list] = mapped_column(JSON, nullable=True, default=list)
    artifacts: Mapped[list] = mapped_column(JSON, nullable=True, default=list)
    credits_quoted: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    credits_charged: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    client_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    payment_method: Mapped[str] = mapped_column(
        String(20), nullable=False, default="credits", server_default="credits"
    )
    x402_receipt: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    callback_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    # Delegation tracking
    delegation_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    parent_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    suggested_agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    suggestion_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    status_history: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    client_agent: Mapped[Optional["Agent"]] = relationship(
        "Agent", back_populates="client_tasks", foreign_keys=[client_agent_id], lazy="selectin"
    )
    provider_agent: Mapped[Optional["Agent"]] = relationship(
        "Agent", back_populates="provider_tasks", foreign_keys=[provider_agent_id], lazy="selectin"
    )
    skill: Mapped[Optional["AgentSkill"]] = relationship(
        "AgentSkill", back_populates="tasks", lazy="selectin"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="task", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, status={self.status})>"
