"""Workflow-channel integration fields.

Links channel_connections to workflows, tracks workflow_runs triggered
by channel messages, and adds failure_mode config to workflows.

Revision ID: 037_workflow_channel_integration
Revises: 036_channel_contacts_privacy
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "037_workflow_channel_integration"
down_revision = "036_channel_contacts_privacy"

branch_labels = None
depends_on = None


def upgrade():
    # channel_connections: link to a workflow + per-connection trigger mappings
    op.add_column(
        "channel_connections",
        sa.Column(
            "workflow_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workflows.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "channel_connections",
        sa.Column("workflow_mappings", sa.JSON(), nullable=True),
    )

    # workflow_runs: back-link to the channel connection + specific chat thread
    op.add_column(
        "workflow_runs",
        sa.Column(
            "channel_connection_id",
            UUID(as_uuid=True),
            sa.ForeignKey("channel_connections.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "workflow_runs",
        sa.Column("channel_chat_id", sa.String(200), nullable=True),
    )

    # channel_messages: link to the workflow run that was triggered
    op.add_column(
        "channel_messages",
        sa.Column(
            "workflow_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workflow_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # workflows: how to handle step failures ("stop" or "continue")
    op.add_column(
        "workflows",
        sa.Column(
            "failure_mode",
            sa.String(20),
            server_default="stop",
            nullable=False,
        ),
    )


def downgrade():
    op.drop_column("workflows", "failure_mode")
    op.drop_column("channel_messages", "workflow_run_id")
    op.drop_column("workflow_runs", "channel_chat_id")
    op.drop_column("workflow_runs", "channel_connection_id")
    op.drop_column("channel_connections", "workflow_mappings")
    op.drop_column("channel_connections", "workflow_id")
