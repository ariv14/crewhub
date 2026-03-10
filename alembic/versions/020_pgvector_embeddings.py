"""Convert embedding column from JSON to pgvector vector(1536).

Enables DB-side cosine similarity search and ~65% storage reduction.
Only runs on PostgreSQL; SQLite (local dev) is unaffected.

Revision ID: 020
Revises: 019
"""

from alembic import op

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return  # Skip on SQLite

    # Enable pgvector extension (pre-installed on Supabase)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Convert JSON → vector(1536)
    # JSON stores [0.1, 0.2, ...] which casts to vector via text representation
    op.execute("""
        ALTER TABLE agent_skills
        ALTER COLUMN embedding
        TYPE vector(1536)
        USING embedding::text::vector(1536)
    """)

    # IVFFlat index for approximate nearest neighbor search
    # lists=1 is optimal for <100 rows; increase when skill count grows
    # (rule of thumb: lists = sqrt(num_rows))
    op.execute("""
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
