"""Add onboarding_completed and interests to users

Revision ID: 010
Revises: 009
Create Date: 2026-02-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("onboarding_completed", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column("users", sa.Column("interests", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "interests")
    op.drop_column("users", "onboarding_completed")
