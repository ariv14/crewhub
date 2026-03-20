"""Add dedicated health monitor columns to agents table.

Moves health state out of the capabilities JSONB field into proper
columns for indexing, querying, and data integrity.

Revision ID: 034
Revises: 033
"""
from alembic import op
import sqlalchemy as sa

revision = "034"
down_revision = "033"


def upgrade() -> None:
    op.add_column("agents", sa.Column("health_failures", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("agents", sa.Column("health_reason", sa.String(50), nullable=True))
    op.add_column("agents", sa.Column("last_health_check_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("agents", sa.Column("last_healthy_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("agents", sa.Column("last_health_latency_ms", sa.Integer(), nullable=True))

    # Migrate existing health data from capabilities JSONB
    op.execute("""
        UPDATE agents SET health_failures = COALESCE(
            (capabilities->>'_health_failures')::int, 0
        )
        WHERE capabilities IS NOT NULL
          AND capabilities->>'_health_failures' IS NOT NULL
    """)

    # Clean up JSONB pollution
    op.execute("""
        UPDATE agents SET capabilities = capabilities - '_health_failures' - '_last_healthy_ms'
        WHERE capabilities IS NOT NULL
          AND (capabilities ? '_health_failures' OR capabilities ? '_last_healthy_ms')
    """)


def downgrade() -> None:
    op.drop_column("agents", "last_health_latency_ms")
    op.drop_column("agents", "last_healthy_at")
    op.drop_column("agents", "last_health_check_at")
    op.drop_column("agents", "health_reason")
    op.drop_column("agents", "health_failures")
