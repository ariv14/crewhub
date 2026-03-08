"""Add production-readiness columns and telemetry table.

Sprint 1: daily_spend_limit on users
Sprint 2: delegation_depth, parent_task_id, suggested_agent_id, suggestion_confidence on tasks
Sprint 2: telemetry_events table

Revision ID: 016
Revises: 015
Create Date: 2026-03-08
"""

from alembic import op
import sqlalchemy as sa

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Sprint 1.2: Per-user spending limits
    op.add_column("users", sa.Column("daily_spend_limit", sa.Float(), nullable=True))

    # Sprint 2.3: Delegation chain depth tracking
    op.add_column(
        "tasks",
        sa.Column("delegation_depth", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "tasks",
        sa.Column(
            "parent_task_id",
            sa.Uuid(),
            sa.ForeignKey("tasks.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Sprint 2.4: Delegation accuracy tracking
    op.add_column(
        "tasks",
        sa.Column(
            "suggested_agent_id",
            sa.Uuid(),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "tasks",
        sa.Column("suggestion_confidence", sa.Float(), nullable=True),
    )

    # Sprint 2.6: Telemetry events table
    op.create_table(
        "telemetry_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=True, index=True),
        sa.Column("event_name", sa.String(100), nullable=False, index=True),
        sa.Column("properties", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("telemetry_events")
    op.drop_column("tasks", "suggestion_confidence")
    op.drop_column("tasks", "suggested_agent_id")
    op.drop_column("tasks", "parent_task_id")
    op.drop_column("tasks", "delegation_depth")
    op.drop_column("users", "daily_spend_limit")
