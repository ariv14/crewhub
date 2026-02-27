"""Add callback_url column to tasks table for A2A push notifications

Revision ID: 003
Revises: 002
Create Date: 2026-02-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("callback_url", sa.String(2048), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tasks", "callback_url")
