import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class AgentStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class VerificationLevel(str, enum.Enum):
    NEW = "new"
    VERIFIED = "verified"
    CERTIFIED = "certified"


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    endpoint: Mapped[str] = mapped_column(String(2048), nullable=False)
    status: Mapped[AgentStatus] = mapped_column(
        String(20), nullable=False, default=AgentStatus.INACTIVE, index=True
    )
    capabilities: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    security_schemes: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    category: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    tags: Mapped[list] = mapped_column(JSON, nullable=True, default=list)
    pricing: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    license_type: Mapped[str] = mapped_column(String(20), nullable=False, default="commercial")
    sla: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    # Agent-level embedding override: {"provider": "gemini", "model": "text-embedding-004"}
    embedding_config: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    accepted_payment_methods: Mapped[list] = mapped_column(
        JSON, nullable=False, default=lambda: ["credits"], server_default='["credits"]'
    )
    mcp_server_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    did_public_key: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    did_private_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    conversation_starters: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    test_cases: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSON, nullable=True, default=dict
    )
    verification_level: Mapped[VerificationLevel] = mapped_column(
        String(20), nullable=False, default=VerificationLevel.NEW
    )
    reputation_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_tasks_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="agents", lazy="selectin")
    skills: Mapped[list["AgentSkill"]] = relationship(
        "AgentSkill", back_populates="agent", lazy="noload", cascade="all, delete-orphan"
    )
    client_tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="client_agent", foreign_keys="[Task.client_agent_id]", lazy="noload"
    )
    provider_tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="provider_agent", foreign_keys="[Task.provider_agent_id]", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name={self.name}, status={self.status})>"
