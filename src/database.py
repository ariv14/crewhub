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

    # Supabase / PgBouncer in transaction mode doesn't support prepared statements
    if "asyncpg" in url and ("pooler.supabase" in url or "pgbouncer" in url):
        kwargs["connect_args"] = {"prepared_statement_cache_size": 0,
                                  "statement_cache_size": 0}
    return kwargs


engine = create_async_engine(
    settings.database_url,
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
