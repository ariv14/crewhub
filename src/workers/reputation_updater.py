import asyncio
import logging
from datetime import UTC, datetime, timedelta

from src.workers import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="src.workers.reputation_updater.apply_reputation_decay")
def apply_reputation_decay():
    """Daily task to decay reputation for inactive agents."""
    asyncio.run(_apply_reputation_decay())


async def _apply_reputation_decay():
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from src.config import settings
    from src.models.agent import Agent
    from src.services.reputation import ReputationService

    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        service = ReputationService(db)

        # Find agents with no tasks in the last 7 days
        cutoff = datetime.now(UTC) - timedelta(days=7)
        result = await db.execute(
            select(Agent).where(Agent.status == "active", Agent.updated_at < cutoff)
        )
        inactive_agents = result.scalars().all()

        logger.info(f"Applying reputation decay to {len(inactive_agents)} inactive agents")

        for agent in inactive_agents:
            weeks = max(1, (datetime.now(UTC) - agent.updated_at.replace(tzinfo=UTC)).days // 7)
            try:
                new_score = await service.apply_decay(agent.id, weeks)
                logger.info(f"Agent {agent.id} reputation decayed to {new_score:.2f}")
            except Exception as e:
                logger.error(f"Error decaying reputation for agent {agent.id}: {e}")

        await db.commit()

    await engine.dispose()


@celery_app.task(name="src.workers.reputation_updater.recalculate_reputation")
def recalculate_reputation(agent_id: str):
    """Recalculate reputation for a specific agent after a task completes."""
    asyncio.run(_recalculate_reputation(agent_id))


async def _recalculate_reputation(agent_id: str):
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from src.config import settings
    from src.services.reputation import ReputationService

    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        service = ReputationService(db)
        new_score = await service.update_reputation(UUID(agent_id))
        logger.info(f"Agent {agent_id} reputation recalculated: {new_score:.2f}")
        await db.commit()

    await engine.dispose()
