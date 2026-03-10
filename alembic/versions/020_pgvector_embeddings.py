"""Convert embedding column from JSON to pgvector vector(N).

Reads EMBEDDING_DIMENSION from env (default 1536).
NULLs existing embeddings first to avoid dimension mismatch during cast.
Embeddings will be regenerated on next agent registration/update.

Only runs on PostgreSQL; SQLite (local dev) is unaffected.

Revision ID: 020
Revises: 019
"""

import os

from alembic import op

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return  # Skip on SQLite

    dim = int(os.environ.get("EMBEDDING_DIMENSION", "1536"))

    # Enable pgvector extension (pre-installed on Supabase)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # NULL out existing embeddings — dimension may mismatch the target vector type
    op.execute("UPDATE agent_skills SET embedding = NULL")

    # Convert JSON → vector(dim)
    op.execute(f"""
        ALTER TABLE agent_skills
        ALTER COLUMN embedding
        TYPE vector({dim})
        USING embedding::text::vector({dim})
    """)

    # IVFFlat index for approximate nearest neighbor search
    # lists=1 is optimal for <100 rows; increase when skill count grows
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

    # Convert vector → JSON
    op.execute("""
        ALTER TABLE agent_skills
        ALTER COLUMN embedding
        TYPE json
        USING embedding::text::json
    """)
