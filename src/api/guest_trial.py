# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Guest trial endpoint — one-shot proxy to A2A agents for unauthenticated users."""

import logging
import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import MarketplaceError, NotFoundError
from src.core.rate_limiter import rate_limit_by_ip
from src.services.content_filter import check_input
from src.database import get_db
from src.models.agent import Agent, AgentStatus
from src.models.skill import AgentSkill
from src.services.a2a_gateway import A2AGatewayService
from src.services.task_broker import TaskBrokerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["guest"])


class GuestTryRequest(BaseModel):
    provider_agent_id: str
    skill_id: str
    message: str = Field(..., min_length=1, max_length=500)


class GuestTryResponse(BaseModel):
    status: str
    artifacts: list[dict]
    message: str | None = None


@router.post(
    "/guest-try",
    response_model=GuestTryResponse,
    dependencies=[Depends(rate_limit_by_ip)],
)
async def guest_try(
    data: GuestTryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> GuestTryResponse:
    """Allow unauthenticated users to try a free agent once (stateless proxy)."""

    # 1. Resolve agent
    try:
        agent_uuid = uuid.UUID(data.provider_agent_id)
    except ValueError:
        raise MarketplaceError(status_code=400, detail="Invalid agent ID")

    result = await db.execute(select(Agent).where(Agent.id == agent_uuid))
    agent = result.scalars().first()
    if not agent:
        raise NotFoundError(detail=f"Agent {data.provider_agent_id} not found")
    if agent.status != AgentStatus.ACTIVE:
        raise NotFoundError(detail=f"Agent {data.provider_agent_id} is not active")

    # 2. Resolve skill
    try:
        skill_uuid = uuid.UUID(data.skill_id)
        skill_filter = (AgentSkill.skill_key == data.skill_id) | (AgentSkill.id == skill_uuid)
    except (ValueError, AttributeError):
        skill_filter = AgentSkill.skill_key == data.skill_id
    result = await db.execute(
        select(AgentSkill).where(AgentSkill.agent_id == agent.id, skill_filter)
    )
    skill = result.scalars().first()
    if not skill:
        raise NotFoundError(detail=f"Skill {data.skill_id} not found on agent")

    # 3. Verify agent is free (0 credits)
    credits = TaskBrokerService._resolve_credits(agent, None, skill.avg_credits)
    if credits > 0:
        raise MarketplaceError(
            status_code=403,
            detail="Guest trial is only available for free community agents. Sign up to try premium agents.",
        )

    # 4. Content moderation — same blocklist as authenticated task creation
    check_input(data.message)

    # 5. Verify agent has an endpoint
    endpoint = agent.endpoint
    if not endpoint:
        raise MarketplaceError(status_code=502, detail="Agent has no endpoint configured")

    # 6. Build A2A task payload and proxy
    task_id = str(uuid.uuid4())
    task_data = {
        "id": task_id,
        "skill_id": skill.skill_key,
        "messages": [
            {
                "role": "user",
                "parts": [{"type": "text", "content": data.message}],
            }
        ],
    }

    try:
        gateway = A2AGatewayService(db)
        response = await gateway.send_task(endpoint, task_data)
    except Exception as exc:
        logger.warning("Guest trial A2A call failed for agent %s: %s", agent.id, exc)
        raise MarketplaceError(status_code=502, detail="Agent is temporarily unavailable")

    # 7. Extract result from JSON-RPC response
    rpc_result = response.get("result", {})
    status = rpc_result.get("status", {})
    status_str = status.get("state", "completed") if isinstance(status, dict) else str(status)

    artifacts = rpc_result.get("artifacts", [])
    # Try to extract a human-readable message from artifacts
    result_message = None
    for artifact in artifacts:
        for part in artifact.get("parts", []):
            if part.get("type") == "text" and part.get("content"):
                result_message = part["content"]
                break
        if result_message:
            break

    return GuestTryResponse(
        status=status_str,
        artifacts=artifacts,
        message=result_message,
    )
