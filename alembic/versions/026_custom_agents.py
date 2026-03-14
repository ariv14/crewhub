"""Add custom_agents, custom_agent_votes, and agent_requests tables.

Revision ID: 026
Revises: 025
"""

import sqlalchemy as sa
from alembic import op

revision = "026"
down_revision = "025"


def upgrade() -> None:
    op.create_table(
        "custom_agents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("category", sa.String(100), nullable=False, server_default="general"),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("source_query", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("try_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_rating", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("upvote_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "promoted_agent_id",
            sa.Uuid(),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
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
        "custom_agent_votes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "custom_agent_id",
            sa.Uuid(),
            sa.ForeignKey("custom_agents.id", ondelete="CASCADE"),
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
        sa.Column("vote", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("custom_agent_id", "user_id", name="uq_custom_agent_vote"),
    )

    op.create_table(
        "agent_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("best_match_confidence", sa.Float(), nullable=True),
        sa.Column(
            "custom_agent_id",
            sa.Uuid(),
            sa.ForeignKey("custom_agents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("agent_requests")
    op.drop_table("custom_agent_votes")
    op.drop_table("custom_agents")
