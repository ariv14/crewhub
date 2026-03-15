# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Health check endpoints for the platform and individual agents."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.agent import Agent
from src.services.health_monitor import HealthMonitorService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Platform health check with database connectivity and agent counts."""
    try:
        await db.execute(text("SELECT 1"))
        total = (await db.execute(select(func.count()).select_from(Agent))).scalar_one()
        active = (
            await db.execute(
                select(func.count()).where(Agent.status == "active")
            )
        ).scalar_one()
        return {
            "status": "healthy",
            "version": "0.1.0",
            "agents_registered": total,
            "agents_active": active,
        }
    except Exception:
        logger.exception("Health check: database unreachable")
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "version": "0.1.0", "detail": "Database unreachable"},
        )


@router.get("/health/debug/db")
async def db_debug(db: AsyncSession = Depends(get_db)):
    """Debug: check column types and alembic version (staging only)."""
    from src.config import settings
    if not settings.debug:
        return {"error": "only available in debug mode"}
    try:
        ver = (await db.execute(text("SELECT version_num FROM alembic_version"))).scalar_one_or_none()
        col = (await db.execute(text(
            "SELECT data_type, udt_name FROM information_schema.columns "
            "WHERE table_name = 'agent_skills' AND column_name = 'embedding'"
        ))).first()
        ext = (await db.execute(text(
            "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'"
        ))).first()
        # Check if pgvector is available
        avail = (await db.execute(text(
            "SELECT name, default_version FROM pg_available_extensions WHERE name = 'vector'"
        ))).first()
        # Try creating extension and capture error
        ext_error = None
        try:
            await db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await db.commit()
        except Exception as e:
            ext_error = str(e)
            await db.rollback()
        return {
            "alembic_version": ver,
            "embedding_column": {"data_type": col[0], "udt_name": col[1]} if col else None,
            "pgvector_ext": {"name": ext[0], "version": ext[1]} if ext else None,
            "pgvector_available": {"name": avail[0], "version": avail[1]} if avail else None,
            "create_ext_error": ext_error,
            "embedding_dimension_setting": settings.embedding_dimension,
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/health/debug/migrate")
async def migrate_debug(db: AsyncSession = Depends(get_db)):
    """Debug: manually trigger alembic and show output (staging only)."""
    from src.config import settings
    if not settings.debug:
        return {"error": "only available in debug mode"}
    import os
    import subprocess
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True, text=True, timeout=30,
            env={**os.environ},
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-2000:] if result.stderr else "",
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/health/agents/{agent_id}")
async def agent_health_check(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Check the health of a specific registered agent.

    Pings the agent's endpoint and returns its availability status,
    response latency, and last-seen timestamp.
    """
    service = HealthMonitorService(db)
    result = await service.get_agent_health(agent_id=agent_id)
    return result
