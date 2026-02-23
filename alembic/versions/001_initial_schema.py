"""Initial schema - all core tables

Revision ID: 001
Revises: None
Create Date: 2026-02-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Agents
    op.create_table(
        "agents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(50), server_default="1.0.0"),
        sa.Column("endpoint", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("capabilities", sa.JSON(), server_default="{}"),
        sa.Column("security_schemes", sa.JSON(), server_default="[]"),
        sa.Column("category", sa.String(100), server_default="general"),
        sa.Column("tags", sa.JSON(), server_default="[]"),
        sa.Column("pricing", sa.JSON(), server_default="{}"),
        sa.Column("sla", sa.JSON(), server_default="{}"),
        sa.Column("verification_level", sa.String(20), server_default="unverified"),
        sa.Column("reputation_score", sa.Float(), server_default="0.0"),
        sa.Column("total_tasks_completed", sa.Integer(), server_default="0"),
        sa.Column("success_rate", sa.Float(), server_default="0.0"),
        sa.Column("avg_latency_ms", sa.Float(), server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agents_owner_id", "agents", ["owner_id"])
    op.create_index("ix_agents_category", "agents", ["category"])
    op.create_index("ix_agents_status", "agents", ["status"])

    # Agent Skills
    op.create_table(
        "agent_skills",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_key", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("input_modes", sa.JSON(), server_default='["text"]'),
        sa.Column("output_modes", sa.JSON(), server_default='["text"]'),
        sa.Column("examples", sa.JSON(), server_default="[]"),
        sa.Column("avg_credits", sa.Float(), server_default="0.0"),
        sa.Column("avg_latency_ms", sa.Integer(), server_default="0"),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_skills_agent_id", "agent_skills", ["agent_id"])

    # Accounts
    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("balance", sa.Numeric(16, 4), server_default="0"),
        sa.Column("reserved", sa.Numeric(16, 4), server_default="0"),
        sa.Column("currency", sa.String(20), server_default="CREDITS"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # Tasks
    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_agent_id", sa.Uuid(), sa.ForeignKey("agents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider_agent_id", sa.Uuid(), sa.ForeignKey("agents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("skill_id", sa.Uuid(), sa.ForeignKey("agent_skills.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), server_default="submitted"),
        sa.Column("messages", sa.JSON(), server_default="[]"),
        sa.Column("artifacts", sa.JSON(), server_default="[]"),
        sa.Column("credits_quoted", sa.Numeric(12, 4), server_default="0"),
        sa.Column("credits_charged", sa.Numeric(12, 4), server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("client_rating", sa.Float(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_client_agent_id", "tasks", ["client_agent_id"])
    op.create_index("ix_tasks_provider_agent_id", "tasks", ["provider_agent_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])

    # Transactions
    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("from_account_id", sa.Uuid(), sa.ForeignKey("accounts.id"), nullable=True),
        sa.Column("to_account_id", sa.Uuid(), sa.ForeignKey("accounts.id"), nullable=True),
        sa.Column("amount", sa.Numeric(16, 4), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("task_id", sa.Uuid(), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transactions_from_account", "transactions", ["from_account_id"])
    op.create_index("ix_transactions_to_account", "transactions", ["to_account_id"])

    # Event log (append-only audit trail)
    op.create_table(
        "event_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("data", sa.JSON(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_event_log_entity", "event_log", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_table("event_log")
    op.drop_table("transactions")
    op.drop_table("tasks")
    op.drop_table("accounts")
    op.drop_table("agent_skills")
    op.drop_table("agents")
    op.drop_table("users")
