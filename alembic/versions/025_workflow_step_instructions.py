"""Add instructions column to workflow_steps.

Revision ID: 025
Revises: 024
"""

import sqlalchemy as sa
from alembic import op

revision = "025"
down_revision = "024"

def upgrade() -> None:
    op.add_column(
        "workflow_steps",
        sa.Column("instructions", sa.Text(), nullable=True),
    )

def downgrade() -> None:
    op.drop_column("workflow_steps", "instructions")
