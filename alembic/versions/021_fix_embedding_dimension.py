"""Fix embedding column if migration 020 ran with wrong dimension or failed.

Handles both cases:
- Column still JSON (020 failed) → convert to vector(N)
- Column is vector(wrong_dim) → re-type to vector(N)

Uses USING NULL to bypass cast issues. Embeddings regenerated on next use.

Revision ID: 021
Revises: 020
"""

import os

from alembic import op

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    dim = int(os.environ.get("EMBEDDING_DIMENSION", "1536"))

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("DROP INDEX IF EXISTS ix_agent_skills_embedding_cosine")
    op.execute("UPDATE agent_skills SET embedding = NULL")

    # USING NULL::vector(dim) works from any source type (json, vector, etc.)
    op.execute(
        f"ALTER TABLE agent_skills ALTER COLUMN embedding "
        f"TYPE vector({dim}) USING NULL::vector({dim})"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_agent_skills_embedding_cosine "
        "ON agent_skills USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 1)"
    )


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    op.execute("DROP INDEX IF EXISTS ix_agent_skills_embedding_cosine")
    op.execute("UPDATE agent_skills SET embedding = NULL")
    op.execute(
        "ALTER TABLE agent_skills ALTER COLUMN embedding "
        "TYPE json USING NULL::json"
    )
