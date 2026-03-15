# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import settings


def _engine_kwargs(url: str, debug: bool) -> dict:
    """Build engine kwargs based on database dialect."""
    # Only echo SQL when explicitly requested via DB_ECHO=1 (too noisy for staging)
    kwargs: dict = {"echo": os.getenv("DB_ECHO", "").strip() in ("1", "true")}

    # SQLite doesn't support connection pool tuning
    if not url.startswith("sqlite"):
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 20
        kwargs["pool_pre_ping"] = True
        kwargs["pool_recycle"] = 3600

    # Supabase / PgBouncer: disable prepared statements + enable SSL
    if "asyncpg" in url and ("pooler.supabase" in url or "pgbouncer" in url):
        kwargs["connect_args"] = {"prepared_statement_cache_size": 0,
                                  "statement_cache_size": 0,
                                  "ssl": "require"}
    return kwargs


def _clean_url(url: str) -> str:
    """Strip sslmode param from asyncpg URLs (handled via connect_args instead)."""
    if "asyncpg" in url and "sslmode=" in url:
        import re
        url = re.sub(r'[?&]sslmode=[^&]*', '', url)
        url = url.replace('?&', '?').rstrip('?')
    return url


engine = create_async_engine(
    _clean_url(settings.database_url),
    **_engine_kwargs(settings.database_url, settings.debug),
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
