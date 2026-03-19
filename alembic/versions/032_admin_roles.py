"""Add admin_role column for RBAC.

Revision ID: 032
Revises: 031
Create Date: 2026-03-19
"""
from alembic import op
import sqlalchemy as sa

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("admin_role", sa.String(20), nullable=True))
    # Backfill: existing admins get super_admin
    op.execute("UPDATE users SET admin_role = 'super_admin' WHERE is_admin = TRUE")


def downgrade() -> None:
    op.drop_column("users", "admin_role")
