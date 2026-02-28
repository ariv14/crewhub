"""Add avatar_url, conversation_starters, test_cases to agents

Revision ID: 007
Revises: 006
Create Date: 2026-02-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("avatar_url", sa.String(2048), nullable=True))
    op.add_column("agents", sa.Column("conversation_starters", sa.JSON(), nullable=True))
    op.add_column("agents", sa.Column("test_cases", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("agents", "test_cases")
    op.drop_column("agents", "conversation_starters")
    op.drop_column("agents", "avatar_url")
