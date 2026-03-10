"""Fix embedding column dimension: vector(1536) → vector(EMBEDDING_DIMENSION).

Staging uses Gemini gemini-embedding-001 which produces 3072-dim vectors.
Reads EMBEDDING_DIMENSION from environment (default 1536 for backwards compat).

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
    if dim == 1536:
        return  # Already correct from migration 020

    # Drop existing index (dimension is changing)
    op.execute("DROP INDEX IF EXISTS ix_agent_skills_embedding_cosine")

    # Wipe embeddings — dimension change means old vectors are incompatible
    op.execute("UPDATE agent_skills SET embedding = NULL")

    # Alter column to new dimension
    op.execute(f"ALTER TABLE agent_skills ALTER COLUMN embedding TYPE vector({dim})")

    # Recreate index
    op.execute(f"""
        CREATE INDEX IF NOT EXISTS ix_agent_skills_embedding_cosine
        ON agent_skills
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 1)
    """)


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    op.execute("DROP INDEX IF EXISTS ix_agent_skills_embedding_cosine")
    op.execute("UPDATE agent_skills SET embedding = NULL")
    op.execute("ALTER TABLE agent_skills ALTER COLUMN embedding TYPE vector(1536)")
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_agent_skills_embedding_cosine
        ON agent_skills
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 1)
    """)
