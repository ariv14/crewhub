"""Health monitor service -- check agent availability and track uptime."""

import time

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config import settings
from src.models.agent import Agent, AgentStatus


class HealthMonitorService:
    """Periodically checks agent endpoints and manages availability status."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Check a single agent
    # ------------------------------------------------------------------

    async def check_agent(self, agent: Agent) -> dict:
        """HTTP GET the agent's well-known agent card endpoint and measure latency.

        Returns:
            A dict with keys: available, latency_ms, error.
        """
        from src.schemas.agent import _validate_public_url

        url = agent.endpoint.rstrip("/") + "/.well-known/agent-card.json"

        # SSRF guard: validate the URL before making the request
        try:
            _validate_public_url(url)
        except ValueError as exc:
            return {
                "agent_id": str(agent.id),
                "available": False,
                "latency_ms": 0,
                "error": f"Invalid endpoint: {exc}",
            }

        try:
            start = time.monotonic()
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
            elapsed_ms = int((time.monotonic() - start) * 1000)

            if response.status_code == 200:
                return {
                    "agent_id": str(agent.id),
                    "available": True,
                    "latency_ms": elapsed_ms,
                    "error": None,
                }
            else:
                return {
                    "agent_id": str(agent.id),
                    "available": False,
                    "latency_ms": elapsed_ms,
                    "error": f"HTTP {response.status_code}",
                }
        except httpx.TimeoutException:
            return {
                "agent_id": str(agent.id),
                "available": False,
                "latency_ms": 10_000,
                "error": "Timeout after 10s",
            }
        except Exception as exc:
            return {
                "agent_id": str(agent.id),
                "available": False,
                "latency_ms": 0,
                "error": str(exc),
            }

    # ------------------------------------------------------------------
    # Check all active agents
    # ------------------------------------------------------------------

    async def check_all_active_agents(self) -> list[dict]:
        """Check every active agent and update status on consecutive failures.

        If an agent fails ``settings.health_check_max_failures`` consecutive
        checks it is marked inactive.
        """
        stmt = (
            select(Agent)
            .options(selectinload(Agent.skills))
            .where(Agent.status == AgentStatus.ACTIVE)
        )
        result = await self.db.execute(stmt)
        agents = list(result.scalars().unique().all())

        results: list[dict] = []
        for agent in agents:
            check = await self.check_agent(agent)
            results.append(check)

            # Track consecutive failures in the agent's capabilities JSONB
            caps = dict(agent.capabilities or {})
            consecutive_failures = caps.get("_health_failures", 0)

            if check["available"]:
                caps["_health_failures"] = 0
                caps["_last_healthy_ms"] = check["latency_ms"]
            else:
                consecutive_failures += 1
                caps["_health_failures"] = consecutive_failures

                if consecutive_failures >= settings.health_check_max_failures:
                    agent.status = AgentStatus.INACTIVE

            agent.capabilities = caps

        await self.db.commit()
        return results

    # ------------------------------------------------------------------
    # Get health for a specific agent
    # ------------------------------------------------------------------

    async def get_agent_health(self, agent_id) -> dict:
        """Return the latest health check result for an agent."""
        from uuid import UUID as _UUID

        agent_uuid = agent_id if isinstance(agent_id, _UUID) else _UUID(str(agent_id))
        agent = await self.db.get(Agent, agent_uuid)
        if not agent:
            return {
                "agent_id": str(agent_id),
                "available": False,
                "latency_ms": 0,
                "error": "Agent not found",
            }

        # Perform a live check
        return await self.check_agent(agent)
