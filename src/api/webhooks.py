"""Webhook endpoints for receiving A2A protocol callbacks from provider agents."""

import hashlib
import hmac
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_db
from src.schemas.a2a import JsonRpcRequest, JsonRpcResponse
from src.services.task_broker import TaskBrokerService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def _verify_webhook_signature(
    request: Request,
    x_webhook_signature: str | None = Header(None, alias="X-Webhook-Signature"),
) -> None:
    """Verify the HMAC-SHA256 webhook signature if a webhook secret is configured."""
    if not settings.webhook_secret:
        return  # No secret configured — skip validation (dev mode)

    if x_webhook_signature is None:
        raise HTTPException(status_code=401, detail="Missing X-Webhook-Signature header")

    body = await request.body()
    expected = hmac.new(
        settings.webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, x_webhook_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


@router.post("/a2a/{agent_id}", response_model=JsonRpcResponse)
async def a2a_callback(
    agent_id: UUID,
    payload: JsonRpcRequest,
    db: AsyncSession = Depends(get_db),
    _sig: None = Depends(_verify_webhook_signature),
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
