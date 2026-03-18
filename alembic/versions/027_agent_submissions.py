# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Add agent_submissions table for no-code builder publish flow.

Revision ID: 027
Revises: 026
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("langflow_flow_id", sa.String(200), nullable=False),
        sa.Column("flow_snapshot", postgresql.JSON(), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("credits", sa.Float(), nullable=False, server_default="10"),
        sa.Column("tags", postgresql.JSON(), server_default="[]"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending_review"),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_submissions_user", "agent_submissions", ["user_id"])
    op.create_index("idx_submissions_status", "agent_submissions", ["status"])


def downgrade() -> None:
    op.drop_index("idx_submissions_status")
    op.drop_index("idx_submissions_user")
    op.drop_table("agent_submissions")
