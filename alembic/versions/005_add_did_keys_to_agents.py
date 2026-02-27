"""Add DID identity columns to agents table

Revision ID: 005
Revises: 004
Create Date: 2026-02-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("did_public_key", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "agents",
        sa.Column("did_private_key_encrypted", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agents", "did_private_key_encrypted")
    op.drop_column("agents", "did_public_key")
