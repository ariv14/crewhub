"""Add timeout_seconds, step_timeout_seconds to workflows; error to workflow_step_runs.

Revision ID: 024
Revises: 023
"""

import sqlalchemy as sa
from alembic import op

revision = "024"
down_revision = "023"


def upgrade() -> None:
    # User-configurable workflow-level timeout (default 1800s = 30 min)
    op.add_column(
        "workflows",
        sa.Column("timeout_seconds", sa.Integer(), nullable=True, server_default="1800"),
    )
    # Per-step timeout (default 120s — matches A2A dispatch timeout)
    op.add_column(
        "workflows",
        sa.Column("step_timeout_seconds", sa.Integer(), nullable=True, server_default="120"),
    )
    # Per-step error detail (why a step failed/timed out)
    op.add_column(
        "workflow_step_runs",
        sa.Column("error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workflow_step_runs", "error")
    op.drop_column("workflows", "step_timeout_seconds")
    op.drop_column("workflows", "timeout_seconds")
