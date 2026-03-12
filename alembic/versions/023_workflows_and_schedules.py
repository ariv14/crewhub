"""Add workflows, workflow_steps, workflow_step_runs, workflow_runs, and schedules tables.

Revision ID: 023
Revises: 022
"""

import sqlalchemy as sa
from alembic import op

revision = "023"
down_revision = "022"


def upgrade() -> None:
    op.create_table(
        "workflows",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "owner_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(10), nullable=False, server_default="🔗"),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("max_total_credits", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "workflow_steps",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workflow_id",
            sa.Uuid(),
            sa.ForeignKey("workflows.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "agent_id",
            sa.Uuid(),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "skill_id",
            sa.Uuid(),
            sa.ForeignKey("agent_skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_group", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_mode", sa.String(20), nullable=False, server_default="chain"),
        sa.Column("input_template", sa.Text(), nullable=True),
        sa.Column("label", sa.String(255), nullable=True),
    )

    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workflow_id",
            sa.Uuid(),
            sa.ForeignKey("workflows.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("schedule_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("current_step_group", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_message", sa.Text(), nullable=False),
        sa.Column("workflow_snapshot", sa.JSON(), nullable=True),
        sa.Column("total_credits_charged", sa.Numeric(12, 4), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "workflow_step_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "run_id",
            sa.Uuid(),
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "step_id",
            sa.Uuid(),
            sa.ForeignKey("workflow_steps.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("task_id", sa.Uuid(), sa.ForeignKey("tasks.id"), nullable=True),
        sa.Column("step_group", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("output_text", sa.Text(), nullable=True),
        sa.Column("credits_charged", sa.Numeric(12, 4), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "schedules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "owner_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("schedule_type", sa.String(20), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("task_params", sa.JSON(), nullable=True),
        sa.Column("cron_expression", sa.String(100), nullable=False),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="UTC"),
        sa.Column("input_message", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("run_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_runs", sa.Integer(), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_consecutive_failures", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("credit_minimum", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("workflow_step_runs")
    op.drop_table("workflow_runs")
    op.drop_table("workflow_steps")
    op.drop_table("workflows")
    op.drop_table("schedules")
