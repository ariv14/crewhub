import asyncio
import logging

from src.workers import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="src.workers.health_checker.check_all_agents")
def check_all_agents():
    """Periodic task to check health of all active agents."""
    asyncio.run(_check_all_agents())


async def _check_all_agents():
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from src.config import settings
    from src.models.agent import Agent
    from src.services.health_monitor import HealthMonitorService

    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        service = HealthMonitorService(db)
        result = await db.execute(select(Agent).where(Agent.status == "active"))
        agents = result.scalars().all()

        logger.info(f"Running health checks for {len(agents)} active agents")

        for agent in agents:
            try:
                health = await service.check_agent(agent)
                if not health["available"]:
                    logger.warning(
                        f"Agent {agent.id} ({agent.name}) health check failed: {health.get('error')}"
                    )
            except Exception as e:
                logger.error(f"Error checking agent {agent.id}: {e}")

        await db.commit()

    await engine.dispose()


@celery_app.task(name="src.workers.health_checker.check_single_agent")
def check_single_agent(agent_id: str):
    """On-demand health check for a specific agent."""
    asyncio.run(_check_single_agent(agent_id))


async def _check_single_agent(agent_id: str):
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from src.config import settings
    from src.services.health_monitor import HealthMonitorService

    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        service = HealthMonitorService(db)
        health = await service.get_agent_health(UUID(agent_id))
        logger.info(f"Agent {agent_id} health: {health}")

    await engine.dispose()
