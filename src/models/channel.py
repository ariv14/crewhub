# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Channel models — multi-channel gateway connections and messages."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class ChannelConnection(Base):
    __tablename__ = "channel_connections"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    platform_bot_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    bot_token: Mapped[str] = mapped_column(Text, nullable=False)  # envelope encrypted
    webhook_secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # envelope encrypted
    bot_name: Mapped[str] = mapped_column(String(200), nullable=False)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    skill_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("agent_skills.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")
    paused_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    daily_credit_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    low_balance_threshold: Mapped[int] = mapped_column(Integer, default=20)
    pause_on_limit: Mapped[bool] = mapped_column(Boolean, default=True)
    webhook_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    privacy_notice_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    message_retention_days: Mapped[Optional[int]] = mapped_column(Integer, server_default="90", nullable=True)
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    gateway_instance_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    workflow_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True
    )
    workflow_mappings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id], lazy="selectin")
    agent: Mapped["Agent"] = relationship("Agent", foreign_keys=[agent_id], lazy="selectin")
    skill: Mapped[Optional["AgentSkill"]] = relationship(
        "AgentSkill", foreign_keys=[skill_id], lazy="selectin"
    )
    messages: Mapped[list["ChannelMessage"]] = relationship(
        "ChannelMessage",
        back_populates="connection",
        lazy="noload",
        cascade="all, delete-orphan",
    )


class ChannelMessage(Base):
    __tablename__ = "channel_messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    connection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("channel_connections.id", ondelete="CASCADE"), nullable=False
    )
    platform_user_id_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    platform_message_id: Mapped[str] = mapped_column(String(200), nullable=False)
    platform_chat_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # inbound|outbound|system
    message_text: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)  # Retained for 90 days, auto-purged
    media_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    workflow_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("workflow_runs.id", ondelete="SET NULL"), nullable=True
    )
    credits_charged: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=0)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    whatsapp_window_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    connection: Mapped["ChannelConnection"] = relationship(
        "ChannelConnection", back_populates="messages", foreign_keys=[connection_id]
    )


class ChannelContactBlock(Base):
    __tablename__ = "channel_contact_blocks"
    __table_args__ = (
        UniqueConstraint("connection_id", "platform_user_id_hash", name="uq_contact_blocks_conn_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    connection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("channel_connections.id", ondelete="CASCADE"), nullable=False
    )
    platform_user_id_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    blocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    blocked_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True
    )
    reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Relationships
    connection: Mapped["ChannelConnection"] = relationship(
        "ChannelConnection", foreign_keys=[connection_id], lazy="selectin"
    )
