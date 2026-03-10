"""Convert embedding column from JSON to pgvector vector(N).

Reads EMBEDDING_DIMENSION from env (default 1536).
NULLs existing embeddings first to avoid dimension mismatch during cast.
Uses HNSW index (supports up to 4096 dims) instead of IVFFlat (max 2000).

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

    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # NULL out existing embeddings — dimension may mismatch the target vector type
    op.execute("UPDATE agent_skills SET embedding = NULL")

    # Convert JSON → vector(dim)
    op.execute(
        f"ALTER TABLE agent_skills ALTER COLUMN embedding "
        f"TYPE vector({dim}) USING embedding::text::vector({dim})"
    )

    # Vector index — only for dimensions <= 2000 (pgvector limit on Supabase)
    # For higher dims (e.g. Gemini 3072), sequential scan is fine at <1000 rows
    if dim <= 2000:
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_agent_skills_embedding_cosine "
            "ON agent_skills USING hnsw (embedding vector_cosine_ops)"
        )


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    op.execute("DROP INDEX IF EXISTS ix_agent_skills_embedding_cosine")
    op.execute(
        "ALTER TABLE agent_skills ALTER COLUMN embedding "
        "TYPE json USING embedding::text::json"
    )
