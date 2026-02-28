"""Fix boolean server_defaults for cross-database compatibility.

Revision ID: 012
Revises: 011
Create Date: 2026-02-28
"""

import sqlalchemy as sa
from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("is_active", server_default=sa.true())
        batch_op.alter_column("is_admin", server_default=sa.false())
        batch_op.alter_column("onboarding_completed", server_default=sa.false())


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("is_active", server_default=sa.text("'true'"))
        batch_op.alter_column("is_admin", server_default=sa.text("'false'"))
        batch_op.alter_column("onboarding_completed", server_default=sa.text("'false'"))
