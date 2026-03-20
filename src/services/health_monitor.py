# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Health monitor service -- check agent availability and track uptime."""

import logging
import time
from collections import defaultdict

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.agent import Agent, AgentStatus

logger = logging.getLogger(__name__)

# In-memory circuit breaker state (fallback when Redis unavailable)
_circuit_failures: dict[str, list[float]] = defaultdict(list)


def is_circuit_open(agent_id: str) -> bool:
    """Check if an agent's circuit breaker is open (too many recent failures).

    Uses Redis if available, falls back to in-memory tracking.
    Returns True if the agent should NOT receive new tasks.
    """
    from src.core.rate_limiter import _get_redis

    threshold = settings.circuit_breaker_threshold
    window = settings.circuit_breaker_window_seconds

    # Try Redis first
    try:
        r = _get_redis()
        if r:
            key = f"circuit:{agent_id}:failures"
            count = r.get(key)
            return int(count or 0) >= threshold
    except Exception:
        pass

    # In-memory fallback
    now = time.time()
    cutoff = now - window
    failures = _circuit_failures[agent_id]
    _circuit_failures[agent_id] = [t for t in failures if t > cutoff]
    return len(_circuit_failures[agent_id]) >= threshold


def record_circuit_failure(agent_id: str) -> None:
    """Record a dispatch failure for circuit breaker tracking."""
    from src.core.rate_limiter import _get_redis

    window = settings.circuit_breaker_window_seconds

    try:
        r = _get_redis()
        if r:
            key = f"circuit:{agent_id}:failures"
            pipe = r.pipeline()
            pipe.incr(key)
            pipe.expire(key, window)
            pipe.execute()
            return
    except Exception:
        pass

    _circuit_failures[agent_id].append(time.time())


def reset_circuit(agent_id: str) -> None:
    """Reset circuit breaker on successful dispatch."""
    from src.core.rate_limiter import _get_redis

    try:
        r = _get_redis()
        if r:
            r.delete(f"circuit:{agent_id}:failures")
            return
    except Exception:
        pass

    _circuit_failures.pop(agent_id, None)


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
        """Check active and unavailable agents, auto-recover on success.

        - ACTIVE agents that fail ``settings.health_check_max_failures``
          consecutive checks are marked UNAVAILABLE (not INACTIVE).
        - UNAVAILABLE agents that respond successfully are auto-promoted
          back to ACTIVE.
        - INACTIVE agents (owner-deactivated) are never touched.
        """
        stmt = (
            select(Agent)
            .where(Agent.status.in_([AgentStatus.ACTIVE, AgentStatus.UNAVAILABLE]))
        )
        result = await self.db.execute(stmt)
        agents = list(result.scalars().unique().all())

        results: list[dict] = []
        for agent in agents:
            try:
                check = await self.check_agent(agent)
                results.append(check)

                caps = dict(agent.capabilities or {})
                consecutive_failures = caps.get("_health_failures", 0)

                if check["available"]:
                    caps["_health_failures"] = 0
                    caps["_last_healthy_ms"] = check["latency_ms"]
                    # Auto-recover unavailable agents
                    if agent.status == AgentStatus.UNAVAILABLE:
                        agent.status = AgentStatus.ACTIVE
                        logger.info(
                            "Agent %s (%s) auto-recovered to ACTIVE",
                            agent.name, agent.id,
                        )
                else:
                    consecutive_failures += 1
                    caps["_health_failures"] = consecutive_failures

                    if (
                        consecutive_failures >= settings.health_check_max_failures
                        and agent.status == AgentStatus.ACTIVE
                    ):
                        agent.status = AgentStatus.UNAVAILABLE
                        logger.warning(
                            "Agent %s (%s) marked UNAVAILABLE after %d failures",
                            agent.name, agent.id, consecutive_failures,
                        )

                agent.capabilities = caps
            except Exception:
                logger.exception("Error checking agent %s", agent.id)

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
