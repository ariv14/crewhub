"""Add status_history column to tasks

Revision ID: 008
Revises: 007
Create Date: 2026-02-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("status_history", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "status_history")
