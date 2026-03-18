# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Webhook endpoints for receiving A2A protocol callbacks from provider agents."""

import hashlib
import hmac
import logging
import time
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_db
from src.schemas.a2a import JsonRpcRequest, JsonRpcResponse
from src.services.task_broker import TaskBrokerService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def _verify_webhook_signature(
    request: Request,
    x_webhook_signature: str | None = Header(None, alias="X-Webhook-Signature"),
) -> None:
    """Verify the HMAC-SHA256 webhook signature if a webhook secret is configured."""
    if not settings.webhook_secret:
        if settings.debug:
            return  # No secret configured — skip validation (debug mode only)
        raise HTTPException(
            status_code=503,
            detail="Webhook verification not configured",
        )

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
    """Receive A2A JSON-RPC callbacks from provider agents."""
    start = time.monotonic()
    service = TaskBrokerService(db)
    response: JsonRpcResponse | None = None
    error_msg: str | None = None
    success = True

    try:
        if payload.method == "tasks/statusUpdate":
            result = await service.handle_status_update(
                agent_id=agent_id,
                params=payload.params,
            )
            response = JsonRpcResponse(id=payload.id, result=result)

        elif payload.method == "tasks/artifactUpdate":
            result = await service.handle_artifact_update(
                agent_id=agent_id,
                params=payload.params,
            )
            response = JsonRpcResponse(id=payload.id, result=result)

        else:
            success = False
            error_msg = f"Method not found: {payload.method}"
            response = JsonRpcResponse(
                id=payload.id,
                error={"code": -32601, "message": error_msg},
            )

    except Exception as exc:
        success = False
        error_msg = str(exc)[:500]
        raise

    finally:
        latency_ms = int((time.monotonic() - start) * 1000)
        task_id_str = payload.params.get("id") if payload.params else None
        task_id = None
        try:
            task_id = uuid.UUID(task_id_str) if task_id_str else None
        except (ValueError, TypeError):
            pass

        try:
            from src.models.webhook_log import WebhookLog
            log = WebhookLog(
                agent_id=agent_id,
                task_id=task_id,
                direction="inbound",
                method=payload.method,
                request_body=payload.model_dump(),
                response_body=response.model_dump() if response else None,
                status_code=200 if success else 400,
                success=success,
                error_message=error_msg,
                latency_ms=latency_ms,
            )
            db.add(log)
            await db.flush()
        except Exception:
            logger.debug("Failed to persist inbound webhook log", exc_info=True)

    return response
