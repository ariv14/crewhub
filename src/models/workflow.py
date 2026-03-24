# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Workflow models — sequential/parallel multi-agent pipelines."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str] = mapped_column(String(10), nullable=False, default="🔗")
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_total_credits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timeout_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True, default=1800)
    step_timeout_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True, default=120)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    pattern_type: Mapped[str] = mapped_column(String, default="manual")
    supervisor_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    failure_mode: Mapped[str] = mapped_column(String(20), default="stop", server_default="stop")

    owner: Mapped["User"] = relationship("User", lazy="selectin")
    steps: Mapped[list["WorkflowStep"]] = relationship(
        "WorkflowStep",
        back_populates="workflow",
        foreign_keys="[WorkflowStep.workflow_id]",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="WorkflowStep.step_group, WorkflowStep.position",
    )
    runs: Mapped[list["WorkflowRun"]] = relationship(
        "WorkflowRun",
        back_populates="workflow",
        lazy="noload",
        cascade="all, delete-orphan",
    )


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("agents.id", ondelete="CASCADE"), nullable=True
    )
    skill_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("agent_skills.id", ondelete="CASCADE"), nullable=True
    )
    sub_workflow_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True
    )
    step_group: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="chain")
    input_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="steps", foreign_keys=[workflow_id])
    agent: Mapped["Agent"] = relationship("Agent", lazy="selectin")
    skill: Mapped["AgentSkill"] = relationship("AgentSkill", lazy="selectin")
    sub_workflow: Mapped[Optional["Workflow"]] = relationship(
        "Workflow", foreign_keys=[sub_workflow_id], lazy="selectin", overlaps="steps,workflow"
    )


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    schedule_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    current_step_group: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_message: Mapped[str] = mapped_column(Text, nullable=False)
    workflow_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    total_credits_charged: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parent_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("workflow_runs.id", ondelete="SET NULL"), nullable=True
    )
    depth: Mapped[int] = mapped_column(Integer, default=0)
    channel_connection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("channel_connections.id", ondelete="SET NULL"), nullable=True
    )
    channel_chat_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="runs")
    parent_run: Mapped[Optional["WorkflowRun"]] = relationship(
        "WorkflowRun", remote_side="WorkflowRun.id", foreign_keys=[parent_run_id]
    )
    step_runs: Mapped[list["WorkflowStepRun"]] = relationship(
        "WorkflowStepRun",
        back_populates="run",
        foreign_keys="[WorkflowStepRun.run_id]",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="WorkflowStepRun.step_group",
    )


class WorkflowStepRun(Base):
    __tablename__ = "workflow_step_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("workflow_steps.id", ondelete="SET NULL"), nullable=True
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("tasks.id"), nullable=True
    )
    step_group: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    output_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    credits_charged: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    child_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("workflow_runs.id", ondelete="SET NULL"), nullable=True
    )

    run: Mapped["WorkflowRun"] = relationship("WorkflowRun", back_populates="step_runs", foreign_keys=[run_id])
