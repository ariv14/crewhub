# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Custom MCP resources beyond the auto-generated FastAPI endpoint tools.

These provide read-only access to agent registry data, categories, and
trending skills in a format optimized for LLM tool use.
"""

from src.database import async_session
from src.models.agent import Agent, AgentStatus
from src.models.skill import AgentSkill
from src.services.registry import RegistryService

from sqlalchemy import func, select


async def get_agent_registry() -> list[dict]:
    """agents://registry — list of all active agents."""
    async with async_session() as db:
        service = RegistryService(db)
        agents, _ = await service.list_agents(page=1, per_page=100, status="active")
        return [
            {
                "id": str(a.id),
                "name": a.name,
                "description": (a.description or "")[:200],
                "category": a.category,
                "version": a.version,
                "reputation_score": a.reputation_score,
                "total_tasks_completed": a.total_tasks_completed,
                "skills": [s.name for s in a.skills],
            }
            for a in agents
        ]


async def get_agent_card(agent_id: str) -> dict:
    """agents://{id}/card — A2A agent card for a specific agent."""
    from uuid import UUID
    async with async_session() as db:
        service = RegistryService(db)
        return await service.get_agent_card(UUID(agent_id))


async def get_discovery_categories() -> list[dict]:
    """discovery://categories — available agent categories with counts."""
    async with async_session() as db:
        stmt = (
            select(Agent.category, func.count(Agent.id))
            .where(Agent.status == AgentStatus.ACTIVE)
            .group_by(Agent.category)
            .order_by(func.count(Agent.id).desc())
        )
        result = await db.execute(stmt)
        return [
            {"category": row[0], "count": row[1]}
            for row in result.all()
        ]


async def get_trending_skills() -> list[dict]:
    """discovery://trending — skills with most completed tasks."""
    async with async_session() as db:
        from src.models.task import Task, TaskStatus
        stmt = (
            select(
                AgentSkill.name,
                AgentSkill.description,
                func.count(Task.id).label("task_count"),
            )
            .join(Task, Task.skill_id == AgentSkill.id)
            .where(Task.status == TaskStatus.COMPLETED)
            .group_by(AgentSkill.id, AgentSkill.name, AgentSkill.description)
            .order_by(func.count(Task.id).desc())
            .limit(20)
        )
        result = await db.execute(stmt)
        return [
            {
                "skill": row[0],
                "description": (row[1] or "")[:200],
                "completed_tasks": row[2],
            }
            for row in result.all()
        ]
