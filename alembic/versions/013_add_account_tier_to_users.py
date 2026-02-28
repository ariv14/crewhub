"""Add account_tier column to users table.

Revision ID: 013
Revises: 012
Create Date: 2026-03-01
"""
from alembic import op
import sqlalchemy as sa

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("account_tier", sa.String(20), nullable=False, server_default="free"),
    )


def downgrade() -> None:
    op.drop_column("users", "account_tier")
