# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Portable vector column type — pgvector on PostgreSQL, JSON on SQLite.

Uses pgvector's Vector type directly (preserving cosine_distance operator),
with a compile-time fallback to JSON on SQLite for local development.
"""

from sqlalchemy import JSON

from src.config import settings


def get_embedding_column_type(dim: int = 1536):
    """Return the appropriate column type for embeddings based on database dialect.

    On PostgreSQL: returns pgvector's Vector(dim) — supports cosine_distance operator.
    On SQLite: returns JSON — embeddings stored as JSON arrays.
    """
    if is_pgvector(settings.database_url):
        from pgvector.sqlalchemy import Vector

        return Vector(dim)
    return JSON()


def is_pgvector(db_url: str) -> bool:
    """Check if the database supports pgvector (PostgreSQL only)."""
    return "postgresql" in db_url or "asyncpg" in db_url
