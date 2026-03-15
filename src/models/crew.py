# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""AgentCrew — saved agent team compositions for reuse."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class AgentCrew(Base):
    __tablename__ = "agent_crews"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str] = mapped_column(String(10), nullable=False, default="🤖")
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", lazy="selectin")  # noqa: F821
    members: Mapped[list["AgentCrewMember"]] = relationship(
        "AgentCrewMember",
        back_populates="crew",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="AgentCrewMember.position",
    )

    def __repr__(self) -> str:
        return f"<AgentCrew(id={self.id}, name={self.name})>"


class AgentCrewMember(Base):
    __tablename__ = "agent_crew_members"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    crew_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("agent_crews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("agent_skills.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    crew: Mapped["AgentCrew"] = relationship("AgentCrew", back_populates="members")
    agent: Mapped["Agent"] = relationship("Agent", lazy="selectin")  # noqa: F821
    skill: Mapped["AgentSkill"] = relationship("AgentSkill", lazy="selectin")  # noqa: F821

    def __repr__(self) -> str:
        return f"<AgentCrewMember(crew_id={self.crew_id}, agent_id={self.agent_id})>"
