"""A2A server-side protocol — JSON-RPC dispatch and SSE streaming.

This router exposes CrewHub as an A2A-compliant server that external agents
can call to create tasks, query status, cancel, and subscribe to real-time
updates via Server-Sent Events.
"""

import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.core.anp_auth import verify_anp_signature
from src.core.rate_limiter import get_rate_limiter
from src.core.exceptions import RateLimitError, UnauthorizedError
from src.database import get_db
from src.models.task import TaskStatus
from src.schemas.a2a import (
    JSONRPC_INTERNAL_ERROR,
    JSONRPC_INVALID_PARAMS,
    JSONRPC_METHOD_NOT_FOUND,
    JSONRPC_TASK_NOT_CANCELABLE,
    JSONRPC_TASK_NOT_FOUND,
    JsonRpcRequest,
    JsonRpcResponse,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
)
from src.services.task_broker import TaskBrokerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/a2a", tags=["a2a"])


# ---------------------------------------------------------------------------
# A2A auth: accept Bearer token, API key, or ANP DID signature
# ---------------------------------------------------------------------------


_bearer_optional = HTTPBearer(auto_error=False)


async def _get_current_user_optional(
    credentials=Depends(_bearer_optional),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> dict | None:
    """Like get_current_user but returns None instead of raising when no creds."""
    if credentials is None and x_api_key is None:
        return None
    return await get_current_user(credentials=credentials, x_api_key=x_api_key)


async def get_a2a_caller(
    current_user: dict | None = Depends(_get_current_user_optional),
    anp_identity: dict | None = Depends(verify_anp_signature),
) -> dict:
    """Resolve the authenticated caller for A2A requests.

    Accepts standard auth (Bearer / API key) or ANP DID signature.
    Returns a dict with at least 'id' key.
    """
    if current_user is not None:
        return current_user
    if anp_identity is not None:
        return {"id": anp_identity["did"], "auth_method": "anp"}
    raise UnauthorizedError(detail="A2A authentication required (Bearer, API key, or ANP signature)")


async def a2a_rate_limit(
    request: Request,
    caller: dict = Depends(get_a2a_caller),
) -> None:
    """Rate-limit A2A requests by caller identity."""
    limiter = get_rate_limiter()
    key = f"a2a:{caller['id']}"
    if not limiter.check(key):
        info = limiter.get_limit_info(key)
        raise RateLimitError(
            detail=f"A2A rate limit exceeded. Try again in {info['reset_in_seconds']} seconds"
        )

TERMINAL_STATUSES = {
    TaskStatus.COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.CANCELED,
    TaskStatus.REJECTED,
}

SSE_POLL_INTERVAL = 2  # seconds
SSE_MAX_DURATION = 300  # 5 minutes max stream


# ---------------------------------------------------------------------------
# JSON-RPC helpers
# ---------------------------------------------------------------------------


def _error_response(rpc_id, code: int, message: str) -> JsonRpcResponse:
    return JsonRpcResponse(id=rpc_id, error={"code": code, "message": message})


def _success_response(rpc_id, result) -> JsonRpcResponse:
    return JsonRpcResponse(id=rpc_id, result=result)


def _task_to_dict(task) -> dict:
    """Serialize a Task model to a JSON-safe dict for A2A responses."""
    return {
        "id": str(task.id),
        "status": task.status.value if hasattr(task.status, "value") else task.status,
        "messages": task.messages or [],
        "artifacts": task.artifacts or [],
        "metadata": {
            "credits_quoted": float(task.credits_quoted) if task.credits_quoted else 0,
            "payment_method": task.payment_method,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        },
    }


# ---------------------------------------------------------------------------
# Main JSON-RPC dispatcher
# ---------------------------------------------------------------------------


@router.post("", dependencies=[Depends(a2a_rate_limit)])
async def a2a_jsonrpc(
    payload: JsonRpcRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    caller: dict = Depends(get_a2a_caller),
):
    """A2A JSON-RPC handler. Dispatches to method handlers.

    Requires authentication (Bearer token, API key, or ANP DID signature)
    and is rate-limited per caller.

    Methods:
      - tasks/send → create task and return result
      - tasks/get → return task status
      - tasks/cancel → cancel task
      - tasks/sendSubscribe → return SSE stream of task updates
    """
    method = payload.method
    params = payload.params
    rpc_id = payload.id

    if method == "tasks/send":
        return await _handle_tasks_send(rpc_id, params, db, caller)
    elif method == "tasks/get":
        return await _handle_tasks_get(rpc_id, params, db)
    elif method == "tasks/cancel":
        return await _handle_tasks_cancel(rpc_id, params, db)
    elif method == "tasks/sendSubscribe":
        return await _handle_tasks_send_subscribe(rpc_id, params, db, caller)
    else:
        return _error_response(rpc_id, JSONRPC_METHOD_NOT_FOUND, f"Method not found: {method}")


# ---------------------------------------------------------------------------
# tasks/send — create a task and return it
# ---------------------------------------------------------------------------


async def _handle_tasks_send(
    rpc_id, params: dict, db: AsyncSession, caller: dict
) -> JsonRpcResponse:
    from src.schemas.agent import _validate_public_url
    from src.schemas.task import TaskCreate, TaskMessage

    try:
        # Extract required fields from A2A params
        provider_agent_id = params.get("provider_agent_id")
        skill_id = params.get("skill_id")
        message_data = params.get("message")

        if not provider_agent_id or not skill_id or not message_data:
            return _error_response(
                rpc_id, JSONRPC_INVALID_PARAMS,
                "Required: provider_agent_id, skill_id, message"
            )

        message = TaskMessage(**message_data)
        task_data = TaskCreate(
            provider_agent_id=UUID(provider_agent_id),
            skill_id=skill_id,
            messages=[message],
            max_credits=params.get("max_credits"),
            tier=params.get("tier"),
        )

        # Use the authenticated caller's ID, not the provider_agent_id from params
        caller_id = caller["id"]
        try:
            user_id = UUID(caller_id)
        except (ValueError, AttributeError):
            # ANP DID callers have a string ID — use a deterministic UUID
            import hashlib
            user_id = UUID(hashlib.md5(str(caller_id).encode()).hexdigest())

        broker = TaskBrokerService(db)
        task = await broker.create_task(task_data, user_id=user_id)

        # Store callback URL if push notification config provided (with SSRF check)
        push_config = params.get("pushNotification")
        if push_config and push_config.get("url"):
            try:
                _validate_public_url(push_config["url"])
            except ValueError as e:
                return _error_response(
                    rpc_id, JSONRPC_INVALID_PARAMS,
                    f"Invalid callback URL: {e}"
                )
            task.callback_url = push_config["url"]
            await db.commit()
            await db.refresh(task)

        return _success_response(rpc_id, _task_to_dict(task))

    except Exception as e:
        logger.exception("tasks/send failed")
        return _error_response(rpc_id, JSONRPC_INTERNAL_ERROR, str(e))


# ---------------------------------------------------------------------------
# tasks/get — query task status
# ---------------------------------------------------------------------------


async def _handle_tasks_get(rpc_id, params: dict, db: AsyncSession) -> JsonRpcResponse:
    task_id = params.get("id")
    if not task_id:
        return _error_response(rpc_id, JSONRPC_INVALID_PARAMS, "Required: id")

    try:
        broker = TaskBrokerService(db)
        task = await broker.get_task(UUID(task_id))
        return _success_response(rpc_id, _task_to_dict(task))
    except Exception as e:
        if "not found" in str(e).lower():
            return _error_response(rpc_id, JSONRPC_TASK_NOT_FOUND, str(e))
        logger.exception("tasks/get failed")
        return _error_response(rpc_id, JSONRPC_INTERNAL_ERROR, str(e))


# ---------------------------------------------------------------------------
# tasks/cancel — cancel a task
# ---------------------------------------------------------------------------


async def _handle_tasks_cancel(rpc_id, params: dict, db: AsyncSession) -> JsonRpcResponse:
    task_id = params.get("id")
    if not task_id:
        return _error_response(rpc_id, JSONRPC_INVALID_PARAMS, "Required: id")

    try:
        broker = TaskBrokerService(db)
        # Cancel without user_id check for A2A server-to-server calls
        task = await broker.get_task(UUID(task_id))

        terminal = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED}
        if task.status in terminal:
            return _error_response(
                rpc_id, JSONRPC_TASK_NOT_CANCELABLE,
                f"Task in '{task.status.value}' state cannot be canceled"
            )

        task = await broker.update_task_status(UUID(task_id), TaskStatus.CANCELED)
        return _success_response(rpc_id, _task_to_dict(task))
    except Exception as e:
        if "not found" in str(e).lower():
            return _error_response(rpc_id, JSONRPC_TASK_NOT_FOUND, str(e))
        logger.exception("tasks/cancel failed")
        return _error_response(rpc_id, JSONRPC_INTERNAL_ERROR, str(e))


# ---------------------------------------------------------------------------
# tasks/sendSubscribe — create task + return SSE stream
# ---------------------------------------------------------------------------


async def _handle_tasks_send_subscribe(
    rpc_id, params: dict, db: AsyncSession, caller: dict
) -> StreamingResponse:
    """Create a task (or subscribe to existing) and stream status updates via SSE."""

    async def event_stream():
        from src.database import async_session

        task_id = params.get("id")

        # If no task_id, create a new task first
        if not task_id:
            try:
                response = await _handle_tasks_send(rpc_id, params, db, caller)
                if response.error:
                    yield f"data: {json.dumps({'error': response.error})}\n\n"
                    return
                task_id = response.result["id"]
                # Yield initial creation event
                yield f"data: {json.dumps(response.result)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': {'code': -32603, 'message': str(e)}})}\n\n"
                return

        # Poll for status changes and stream them
        last_status = None
        last_artifact_count = 0
        elapsed = 0

        while elapsed < SSE_MAX_DURATION:
            try:
                async with async_session() as poll_db:
                    broker = TaskBrokerService(poll_db)
                    task = await broker.get_task(UUID(task_id))

                    current_status = task.status.value if hasattr(task.status, "value") else task.status
                    current_artifacts = task.artifacts or []

                    # Emit status update if changed
                    if current_status != last_status:
                        is_final = task.status in TERMINAL_STATUSES
                        event = TaskStatusUpdateEvent(
                            id=str(task.id),
                            status=current_status,
                            final=is_final,
                        )
                        yield f"event: status\ndata: {event.model_dump_json()}\n\n"
                        last_status = current_status

                        if is_final:
                            # Emit final task state and close
                            yield f"event: done\ndata: {json.dumps(_task_to_dict(task))}\n\n"
                            return

                    # Emit artifact updates if new ones appeared
                    if len(current_artifacts) > last_artifact_count:
                        for artifact in current_artifacts[last_artifact_count:]:
                            event = TaskArtifactUpdateEvent(
                                id=str(task.id),
                                artifact=artifact,
                            )
                            yield f"event: artifact\ndata: {event.model_dump_json()}\n\n"
                        last_artifact_count = len(current_artifacts)

            except Exception as e:
                logger.error(f"SSE poll error for task {task_id}: {e}")
                yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
                return

            await asyncio.sleep(SSE_POLL_INTERVAL)
            elapsed += SSE_POLL_INTERVAL

        # Timed out
        yield f"event: timeout\ndata: {json.dumps({'message': 'Stream max duration reached'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
