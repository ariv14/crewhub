# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Health monitor service -- check agent availability and track uptime."""

import asyncio
import logging
import random
import time
from collections import defaultdict
from datetime import datetime, timezone

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.agent import Agent, AgentStatus

logger = logging.getLogger(__name__)

# In-memory circuit breaker state (fallback when Redis unavailable)
_circuit_failures: dict[str, list[float]] = defaultdict(list)

# Health check configuration
_HEALTH_CHECK_TIMEOUT = 10.0
_WAKE_PROBE_TIMEOUT = 60.0  # Longer timeout for sleeping HF Spaces
_CONCURRENCY_LIMIT = 10

# HTTP status codes that mean "alive but not serving agent card"
_ALIVE_STATUS_CODES = {401, 403, 429}

# HF Spaces sleep indicators
_HF_SLEEP_INDICATORS = {"is sleeping", "space is paused", "space is sleeping"}


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


def _is_hf_space(endpoint: str) -> bool:
    """Check if an endpoint is a HuggingFace Space."""
    return ".hf.space" in endpoint if endpoint else False


def _detect_sleep(status_code: int, error: str | None) -> bool:
    """Detect if a health check failure looks like a sleeping HF Space."""
    if status_code == 503:
        return True
    if error:
        lower = error.lower()
        return any(indicator in lower for indicator in _HF_SLEEP_INDICATORS)
    return False


class HealthMonitorService:
    """Periodically checks agent endpoints and manages availability status."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Check a single agent
    # ------------------------------------------------------------------

    async def check_agent(
        self,
        agent: Agent,
        client: httpx.AsyncClient | None = None,
        wake_probe: bool = False,
    ) -> dict:
        """HTTP GET the agent's well-known agent card endpoint and measure latency.

        Args:
            agent: Agent to check.
            client: Shared httpx client (optional).
            wake_probe: If True, use a longer timeout (60s) to allow cold start.

        Returns:
            A dict with keys: available, latency_ms, error, status_code, sleeping.
        """
        from src.schemas.agent import _validate_public_url

        if not agent.endpoint:
            return {
                "agent_id": str(agent.id),
                "available": False,
                "latency_ms": 0,
                "status_code": 0,
                "error": "No endpoint configured",
                "sleeping": False,
            }

        url = agent.endpoint.rstrip("/") + "/.well-known/agent-card.json"

        # SSRF guard
        try:
            _validate_public_url(url)
        except ValueError as exc:
            return {
                "agent_id": str(agent.id),
                "available": False,
                "latency_ms": 0,
                "status_code": 0,
                "error": f"Invalid endpoint: {exc}",
                "sleeping": False,
            }

        timeout = _WAKE_PROBE_TIMEOUT if wake_probe else _HEALTH_CHECK_TIMEOUT

        try:
            own_client = client is None
            if own_client:
                client = httpx.AsyncClient(timeout=timeout)

            try:
                start = time.monotonic()
                response = await client.get(
                    url, headers={"User-Agent": "CrewHub-HealthMonitor/1.0"},
                )
                elapsed_ms = int((time.monotonic() - start) * 1000)

                if response.status_code == 200:
                    return {
                        "agent_id": str(agent.id),
                        "available": True,
                        "latency_ms": elapsed_ms,
                        "status_code": 200,
                        "error": None,
                        "sleeping": False,
                    }
                elif response.status_code in _ALIVE_STATUS_CODES:
                    return {
                        "agent_id": str(agent.id),
                        "available": True,
                        "latency_ms": elapsed_ms,
                        "status_code": response.status_code,
                        "error": f"HTTP {response.status_code} (alive, not counted as failure)",
                        "sleeping": False,
                    }
                else:
                    body = ""
                    try:
                        body = response.text[:200]
                    except Exception:
                        pass
                    sleeping = _detect_sleep(response.status_code, body)
                    return {
                        "agent_id": str(agent.id),
                        "available": False,
                        "latency_ms": elapsed_ms,
                        "status_code": response.status_code,
                        "error": f"HTTP {response.status_code}",
                        "sleeping": sleeping,
                    }
            finally:
                if own_client:
                    await client.aclose()

        except httpx.TimeoutException:
            return {
                "agent_id": str(agent.id),
                "available": False,
                "latency_ms": int(timeout * 1000),
                "status_code": 0,
                "error": f"Timeout after {int(timeout)}s",
                "sleeping": _is_hf_space(agent.endpoint),
            }
        except Exception as exc:
            return {
                "agent_id": str(agent.id),
                "available": False,
                "latency_ms": 0,
                "status_code": 0,
                "error": str(exc),
                "sleeping": False,
            }

    # ------------------------------------------------------------------
    # Check all active agents (concurrent, with wake probes)
    # ------------------------------------------------------------------

    async def check_all_active_agents(self) -> list[dict]:
        """Check active and unavailable agents concurrently, auto-recover on success.

        - ACTIVE agents that fail ``settings.health_check_max_failures``
          consecutive checks are marked UNAVAILABLE.
        - UNAVAILABLE agents with health_reason='sleeping' get a wake probe
          (60s timeout) to allow HF Spaces cold start.
        - UNAVAILABLE agents that respond successfully are auto-promoted
          back to ACTIVE.
        - INACTIVE agents (owner-deactivated) are never touched.
        - 401/403/429 responses are treated as "alive".
        - Each status change is audit-logged.
        """
        from src.core.audit import audit_log

        stmt = (
            select(Agent)
            .where(Agent.status.in_([AgentStatus.ACTIVE, AgentStatus.UNAVAILABLE]))
        )
        result = await self.db.execute(stmt)
        agents = list(result.scalars().unique().all())

        if not agents:
            return []

        # Concurrent health checks with semaphore
        sem = asyncio.Semaphore(_CONCURRENCY_LIMIT)
        now = datetime.now(timezone.utc)

        async def _check_with_limit(agent: Agent, client: httpx.AsyncClient) -> dict:
            async with sem:
                # Use wake probe for sleeping agents (longer timeout)
                use_wake = (
                    agent.status == AgentStatus.UNAVAILABLE
                    and agent.health_reason == "sleeping"
                )
                return await self.check_agent(agent, client=client, wake_probe=use_wake)

        async with httpx.AsyncClient(
            timeout=_WAKE_PROBE_TIMEOUT,  # Use longer timeout for pool
            limits=httpx.Limits(max_connections=_CONCURRENCY_LIMIT),
        ) as client:
            check_tasks = [_check_with_limit(a, client) for a in agents]
            check_results = await asyncio.gather(*check_tasks, return_exceptions=True)

        # Process results and update statuses
        results: list[dict] = []
        for agent, check in zip(agents, check_results):
            try:
                if isinstance(check, Exception):
                    logger.exception("Health check exception for %s", agent.id, exc_info=check)
                    results.append({
                        "agent_id": str(agent.id),
                        "available": False,
                        "latency_ms": 0,
                        "error": str(check),
                    })
                    continue

                results.append(check)
                old_status = agent.status
                agent.last_health_check_at = now

                if check["available"]:
                    agent.health_failures = 0
                    agent.health_reason = None
                    agent.last_healthy_at = now
                    agent.last_health_latency_ms = check["latency_ms"]
                    # Auto-recover unavailable agents
                    if agent.status == AgentStatus.UNAVAILABLE:
                        agent.status = AgentStatus.ACTIVE
                        logger.info(
                            "Agent %s (%s) auto-recovered to ACTIVE",
                            agent.name, agent.id,
                        )
                else:
                    agent.health_failures = (agent.health_failures or 0) + 1

                    # Set health reason
                    if check.get("sleeping"):
                        agent.health_reason = "sleeping"
                    else:
                        agent.health_reason = "failed"

                    if (
                        agent.health_failures >= settings.health_check_max_failures
                        and agent.status == AgentStatus.ACTIVE
                    ):
                        agent.status = AgentStatus.UNAVAILABLE
                        logger.warning(
                            "Agent %s (%s) marked UNAVAILABLE after %d failures: %s",
                            agent.name, agent.id, agent.health_failures,
                            check.get("error", "unknown"),
                        )

                # Audit log status changes
                if agent.status != old_status:
                    await audit_log(
                        self.db,
                        action="health_monitor.status_change",
                        actor_user_id=None,
                        target_type="agent",
                        target_id=str(agent.id),
                        old_value={"status": old_status.value if hasattr(old_status, "value") else old_status},
                        new_value={
                            "status": agent.status.value if hasattr(agent.status, "value") else agent.status,
                            "health_failures": agent.health_failures,
                            "health_reason": agent.health_reason,
                            "last_error": check.get("error"),
                        },
                    )

            except Exception:
                logger.exception("Error processing health result for agent %s", agent.id)

        await self.db.commit()
        return results

    # ------------------------------------------------------------------
    # Bulk reactivate
    # ------------------------------------------------------------------

    async def bulk_reactivate_unavailable(self) -> int:
        """Reactivate all UNAVAILABLE agents back to ACTIVE. Returns count."""
        stmt = select(Agent).where(Agent.status == AgentStatus.UNAVAILABLE)
        result = await self.db.execute(stmt)
        agents = list(result.scalars().all())

        for agent in agents:
            agent.status = AgentStatus.ACTIVE
            agent.health_failures = 0
            agent.health_reason = None

        if agents:
            await self.db.commit()
            logger.info("Bulk reactivated %d unavailable agents", len(agents))

        return len(agents)

    # ------------------------------------------------------------------
    # Health overview
    # ------------------------------------------------------------------

    async def get_health_overview(self) -> dict:
        """Return aggregate health stats for all agents."""
        stmt = select(
            Agent.status,
            func.count().label("count"),
        ).group_by(Agent.status)
        result = await self.db.execute(stmt)
        rows = result.all()

        status_counts = {row.status: row.count for row in rows}
        total = sum(status_counts.values())

        # Get agents with health issues
        failing_stmt = (
            select(Agent.id, Agent.name, Agent.health_failures, Agent.health_reason,
                   Agent.last_health_latency_ms, Agent.last_health_check_at, Agent.status)
            .where(Agent.status.in_([AgentStatus.ACTIVE, AgentStatus.UNAVAILABLE]))
            .where(Agent.health_failures > 0)
            .order_by(Agent.health_failures.desc())
        )
        failing_result = await self.db.execute(failing_stmt)
        failing_agents = [
            {
                "id": str(row.id),
                "name": row.name,
                "status": row.status,
                "health_failures": row.health_failures,
                "health_reason": row.health_reason,
                "last_latency_ms": row.last_health_latency_ms,
                "last_check_at": row.last_health_check_at.isoformat() if row.last_health_check_at else None,
            }
            for row in failing_result.all()
        ]

        return {
            "total": total,
            "active": status_counts.get(AgentStatus.ACTIVE, 0),
            "unavailable": status_counts.get(AgentStatus.UNAVAILABLE, 0),
            "inactive": status_counts.get(AgentStatus.INACTIVE, 0),
            "suspended": status_counts.get(AgentStatus.SUSPENDED, 0),
            "failing_agents": failing_agents,
        }

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

        return await self.check_agent(agent)
