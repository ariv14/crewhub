"""Add GDPR compliance columns to users table.

Revision ID: 031
Revises: 030
Create Date: 2026-03-19
"""
from alembic import op
import sqlalchemy as sa

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("consent_version", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("consent_given_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("consent_ip", sa.String(45), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "consent_ip")
    op.drop_column("users", "consent_given_at")
    op.drop_column("users", "consent_version")
    op.drop_column("users", "deletion_requested_at")
