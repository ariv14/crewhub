"""Portable vector column type — pgvector on PostgreSQL, JSON on SQLite."""

from sqlalchemy import JSON, func
from sqlalchemy.types import TypeDecorator


class VectorType(TypeDecorator):
    """Stores embedding vectors. Uses pgvector's vector type on PostgreSQL
    for efficient storage and DB-side cosine similarity. Falls back to JSON
    on SQLite for local development.

    Usage in models:
        embedding = deferred(mapped_column(VectorType(1536), nullable=True))

    Usage in queries (PostgreSQL only):
        AgentSkill.embedding.cosine_distance(query_vec)
    """

    impl = JSON
    cache_ok = True

    def __init__(self, dim: int = 1536):
        super().__init__()
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector

            return dialect.type_descriptor(Vector(self.dim))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            # pgvector accepts list[float] directly
            return value
        # SQLite: store as JSON array
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        # pgvector returns numpy array; ensure we return list[float]
        if hasattr(value, "tolist"):
            return value.tolist()
        return list(value) if not isinstance(value, list) else value


def is_pgvector(db_url: str) -> bool:
    """Check if the database supports pgvector (PostgreSQL only)."""
    return "postgresql" in db_url or "asyncpg" in db_url
