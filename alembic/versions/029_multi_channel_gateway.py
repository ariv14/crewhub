# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Add channel_connections and channel_messages tables for multi-channel gateway.

Revision ID: 029
Revises: 028
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- channel_connections --
    op.create_table(
        "channel_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("platform_bot_id", sa.String(200), nullable=True),
        sa.Column("bot_token", sa.Text(), nullable=False),
        sa.Column("webhook_secret", sa.Text(), nullable=True),
        sa.Column("bot_name", sa.String(200), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_skills.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("paused_reason", sa.String(50), nullable=True),
        sa.Column("daily_credit_limit", sa.Integer(), nullable=True),
        sa.Column("low_balance_threshold", sa.Integer(), server_default="20"),
        sa.Column("pause_on_limit", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("webhook_url", sa.String(), nullable=True),
        sa.Column("config", postgresql.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("gateway_instance_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_channel_connections_owner", "channel_connections", ["owner_id"])
    op.create_index("ix_channel_connections_platform_status", "channel_connections", ["platform", "status"])

    # -- channel_messages --
    op.create_table(
        "channel_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("channel_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform_user_id", sa.String(200), nullable=False),
        sa.Column("platform_message_id", sa.String(200), nullable=False),
        sa.Column("platform_chat_id", sa.String(200), nullable=True),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("media_type", sa.String(20), nullable=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("credits_charged", sa.Numeric(12, 4), server_default="0"),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("whatsapp_window_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_channel_messages_connection_created", "channel_messages", ["connection_id", "created_at"])
    op.create_index(
        "ux_channel_messages_dedup",
        "channel_messages",
        ["connection_id", "platform_message_id", "direction"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_channel_messages_dedup", table_name="channel_messages")
    op.drop_index("ix_channel_messages_connection_created", table_name="channel_messages")
    op.drop_table("channel_messages")

    op.drop_index("ix_channel_connections_platform_status", table_name="channel_connections")
    op.drop_index("ix_channel_connections_owner", table_name="channel_connections")
    op.drop_table("channel_connections")
