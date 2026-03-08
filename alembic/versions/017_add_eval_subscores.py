"""Add eval subscores and model tracking to tasks.

Stores per-dimension quality scores (relevance, completeness, coherence)
and the eval model used, enabling multi-model benchmarking.

Revision ID: 017
Revises: 016
Create Date: 2026-03-08
"""

from alembic import op
import sqlalchemy as sa

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("eval_model", sa.String(100), nullable=True))
    op.add_column("tasks", sa.Column("eval_relevance", sa.Float, nullable=True))
    op.add_column("tasks", sa.Column("eval_completeness", sa.Float, nullable=True))
    op.add_column("tasks", sa.Column("eval_coherence", sa.Float, nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "eval_coherence")
    op.drop_column("tasks", "eval_completeness")
    op.drop_column("tasks", "eval_relevance")
    op.drop_column("tasks", "eval_model")
