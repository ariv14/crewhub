# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Agent submission model — flows submitted for marketplace review."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID as PG_UUID
from sqlalchemy.orm import relationship

from src.database import Base


class AgentSubmission(Base):
    __tablename__ = "agent_submissions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    langflow_flow_id = Column(String(200), nullable=False)
    flow_snapshot = Column(JSON, nullable=True)  # frozen flow JSON at approval time
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)
    credits = Column(Float, nullable=False, default=10)
    tags = Column(JSON, default=list)
    status = Column(String(20), nullable=False, default="pending_review", index=True)
    reviewer_notes = Column(Text, nullable=True)
    reviewed_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    agent_id = Column(PG_UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    agent = relationship("Agent", foreign_keys=[agent_id])
