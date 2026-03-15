# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Custom agents — community-created agent prototypes via LLM meta-prompting."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class CustomAgentStatus(str, enum.Enum):
    active = "active"
    promoted = "promoted"
    archived = "archived"


class CustomAgent(Base):
    __tablename__ = "custom_agents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="general")
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_query: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CustomAgentStatus.active.value
    )
    try_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    upvote_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    promoted_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    created_by: Mapped["User"] = relationship("User", lazy="selectin")  # noqa: F821
    promoted_agent: Mapped["Agent"] = relationship("Agent", lazy="noload")  # noqa: F821
    votes: Mapped[list["CustomAgentVote"]] = relationship(
        "CustomAgentVote",
        back_populates="custom_agent",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<CustomAgent(id={self.id}, name={self.name})>"


class CustomAgentVote(Base):
    __tablename__ = "custom_agent_votes"
    __table_args__ = (
        UniqueConstraint("custom_agent_id", "user_id", name="uq_custom_agent_vote"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    custom_agent_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("custom_agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vote: Mapped[int] = mapped_column(Integer, nullable=False)  # +1 or -1
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    custom_agent: Mapped["CustomAgent"] = relationship("CustomAgent", back_populates="votes")

    def __repr__(self) -> str:
        return f"<CustomAgentVote(agent={self.custom_agent_id}, user={self.user_id}, vote={self.vote})>"


class AgentRequest(Base):
    """Demand signal — captures every low-confidence search."""
    __tablename__ = "agent_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    best_match_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    custom_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("custom_agents.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<AgentRequest(id={self.id}, query={self.query[:40]})>"
