# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
import uuid

from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, deferred, mapped_column, relationship

from src.config import settings
from src.core.vector_type import get_embedding_column_type
from src.database import Base


class AgentSkill(Base):
    __tablename__ = "agent_skills"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_key: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    input_modes: Mapped[list] = mapped_column(JSON, nullable=True, default=list)
    output_modes: Mapped[list] = mapped_column(JSON, nullable=True, default=list)
    examples: Mapped[list] = mapped_column(JSON, nullable=True, default=list)
    avg_credits: Mapped[float] = mapped_column(Float, nullable=True)
    avg_latency_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    embedding: Mapped[list] = deferred(mapped_column(get_embedding_column_type(settings.embedding_dimension), nullable=True))

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="skills", lazy="noload")
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="skill", lazy="noload")

    def __repr__(self) -> str:
        return f"<AgentSkill(id={self.id}, name={self.name}, skill_key={self.skill_key})>"
