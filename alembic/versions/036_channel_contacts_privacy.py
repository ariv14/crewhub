"""Channel contact blocks, privacy notice URL, message retention, and indexes."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "036_channel_contacts_privacy"
down_revision = "034"

branch_labels = None
depends_on = None


def upgrade():
    # Contact blocks table
    op.create_table(
        "channel_contact_blocks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("connection_id", UUID(as_uuid=True), sa.ForeignKey("channel_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform_user_id_hash", sa.String(200), nullable=False),
        sa.Column("blocked_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("blocked_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reason", sa.String(200), nullable=True),
        sa.UniqueConstraint("connection_id", "platform_user_id_hash", name="uq_contact_blocks_conn_user"),
    )

    # Privacy notice URL on channel_connections
    op.add_column("channel_connections", sa.Column("privacy_notice_url", sa.String(500), nullable=True))

    # Message retention config (per-channel, default 90 days)
    op.add_column("channel_connections", sa.Column("message_retention_days", sa.Integer(), server_default="90", nullable=True))

    # Fix message_text to be nullable (inbound messages will store NULL)
    op.alter_column("channel_messages", "message_text", nullable=True, existing_type=sa.String(2000))

    # Rename platform_user_id → platform_user_id_hash for clarity
    op.alter_column("channel_messages", "platform_user_id", new_column_name="platform_user_id_hash")

    # Performance index for contacts aggregation
    op.create_index(
        "ix_channel_messages_conn_user_created",
        "channel_messages",
        ["connection_id", "platform_user_id_hash", sa.text("created_at DESC")],
    )


def downgrade():
    op.drop_index("ix_channel_messages_conn_user_created")
    op.alter_column("channel_messages", "platform_user_id_hash", new_column_name="platform_user_id")
    op.alter_column("channel_messages", "message_text", nullable=False, existing_type=sa.String(2000))
    op.drop_column("channel_connections", "message_retention_days")
    op.drop_column("channel_connections", "privacy_notice_url")
    op.drop_table("channel_contact_blocks")
