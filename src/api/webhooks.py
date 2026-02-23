"""Webhook endpoints for receiving A2A protocol callbacks from provider agents."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas.a2a import JsonRpcRequest, JsonRpcResponse
from src.services.task_broker import TaskBrokerService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/a2a/{agent_id}", response_model=JsonRpcResponse)
async def a2a_callback(
    agent_id: UUID,
    payload: JsonRpcRequest,
    db: AsyncSession = Depends(get_db),
) -> JsonRpcResponse:
    """Receive A2A JSON-RPC callbacks from provider agents.

    This is the endpoint that provider agents invoke when a task's status
    changes (e.g. working -> completed, working -> input_required, or
    working -> failed).  The payload follows the A2A JSON-RPC format.

    Supported methods:
      - ``tasks/statusUpdate``  -- update task status and optionally attach artifacts
      - ``tasks/artifactUpdate`` -- append new artifacts to a task

    Returns a JSON-RPC response acknowledging receipt of the callback.
    """
    service = TaskBrokerService(db)

    if payload.method == "tasks/statusUpdate":
        result = await service.handle_status_update(
            agent_id=agent_id,
            params=payload.params,
        )
        return JsonRpcResponse(id=payload.id, result=result)

    if payload.method == "tasks/artifactUpdate":
        result = await service.handle_artifact_update(
            agent_id=agent_id,
            params=payload.params,
        )
        return JsonRpcResponse(id=payload.id, result=result)

    return JsonRpcResponse(
        id=payload.id,
        error={
            "code": -32601,
            "message": f"Method not found: {payload.method}",
        },
    )
