"""A2A gateway service -- JSON-RPC 2.0 communication with external agents."""

import logging
import time
import uuid
from typing import AsyncGenerator

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class A2AGatewayService:
    """Sends JSON-RPC 2.0 requests to remote A2A-compliant agent endpoints."""

    JSON_RPC_VERSION = "2.0"
    DEFAULT_TIMEOUT = 120.0

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_request(self, method: str, params: dict) -> dict:
        """Build a JSON-RPC 2.0 request payload."""
        return {
            "jsonrpc": self.JSON_RPC_VERSION,
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params,
        }

    async def _post(
        self, endpoint: str, method: str, params: dict, timeout: float | None = None
    ) -> dict:
        """Send a JSON-RPC POST and return the parsed response."""
        payload = self._build_request(method, params)
        start = time.monotonic()
        status_code = None
        response_body = None
        error_msg = None
        success = True

        try:
            async with httpx.AsyncClient(timeout=timeout or self.DEFAULT_TIMEOUT) as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                status_code = response.status_code
                response_body = response.json()
                response.raise_for_status()
                return response_body
        except Exception as exc:
            success = False
            error_msg = str(exc)[:500]
            raise
        finally:
            latency_ms = int((time.monotonic() - start) * 1000)
            # Extract agent_id and task_id from params for logging
            task_id_str = params.get("id")
            await self._log_webhook(
                agent_id=None,  # resolved by caller if needed
                task_id_str=task_id_str,
                direction="outbound",
                method=method,
                request_body=payload,
                response_body=response_body,
                status_code=status_code,
                success=success,
                error_message=error_msg,
                latency_ms=latency_ms,
            )

    async def _log_webhook(
        self,
        *,
        agent_id: uuid.UUID | None,
        task_id_str: str | None,
        direction: str,
        method: str,
        request_body: dict | None,
        response_body: dict | None,
        status_code: int | None,
        success: bool,
        error_message: str | None,
        latency_ms: int | None,
    ) -> None:
        """Persist a webhook log entry. Best-effort — never fails the caller."""
        try:
            from src.models.webhook_log import WebhookLog

            task_id = uuid.UUID(task_id_str) if task_id_str else None
            # If agent_id not provided, try to resolve from task
            if agent_id is None and task_id:
                from src.models.task import Task
                from sqlalchemy import select
                result = await self.db.execute(
                    select(Task.provider_agent_id).where(Task.id == task_id)
                )
                row = result.first()
                if row:
                    agent_id = row[0]

            if agent_id is None:
                return  # Can't log without agent_id

            log = WebhookLog(
                agent_id=agent_id,
                task_id=task_id,
                direction=direction,
                method=method,
                request_body=request_body,
                response_body=response_body,
                status_code=status_code,
                success=success,
                error_message=error_message,
                latency_ms=latency_ms,
            )
            self.db.add(log)
            await self.db.flush()
        except Exception:
            logger.debug("Failed to persist webhook log", exc_info=True)

    # ------------------------------------------------------------------
    # Send task
    # ------------------------------------------------------------------

    async def send_task(self, agent_endpoint: str, task_data: dict) -> dict:
        """Send a task to a remote agent via JSON-RPC ``tasks/send``.

        Args:
            agent_endpoint: The base URL of the remote agent.
            task_data: The task payload conforming to the A2A spec.

        Returns:
            The JSON-RPC response body.
        """
        return await self._post(agent_endpoint, "tasks/send", task_data)

    # ------------------------------------------------------------------
    # Get task status
    # ------------------------------------------------------------------

    async def get_task_status(self, agent_endpoint: str, task_id: str) -> dict:
        """Query the status of a task via JSON-RPC ``tasks/get``.

        Args:
            agent_endpoint: The base URL of the remote agent.
            task_id: The identifier of the task.

        Returns:
            The JSON-RPC response body.
        """
        return await self._post(agent_endpoint, "tasks/get", {"id": task_id})

    # ------------------------------------------------------------------
    # Cancel task
    # ------------------------------------------------------------------

    async def cancel_task(self, agent_endpoint: str, task_id: str) -> dict:
        """Cancel a task via JSON-RPC ``tasks/cancel``.

        Args:
            agent_endpoint: The base URL of the remote agent.
            task_id: The identifier of the task.

        Returns:
            The JSON-RPC response body.
        """
        return await self._post(agent_endpoint, "tasks/cancel", {"id": task_id})

    # ------------------------------------------------------------------
    # Stream task (SSE)
    # ------------------------------------------------------------------

    async def stream_task(
        self, agent_endpoint: str, task_id: str
    ) -> AsyncGenerator[dict, None]:
        """Stream task updates via SSE from the remote agent.

        Connects to the agent endpoint and yields parsed events as they arrive.

        Args:
            agent_endpoint: The base URL of the remote agent.
            task_id: The identifier of the task.

        Yields:
            Parsed event dicts from the SSE stream.
        """
        payload = self._build_request("tasks/sendSubscribe", {"id": task_id})

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                agent_endpoint,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                },
            ) as response:
                response.raise_for_status()
                event_data = ""
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        event_data = line[6:]
                        try:
                            import json
                            yield json.loads(event_data)
                        except (ValueError, TypeError):
                            yield {"raw": event_data}
                        event_data = ""
                    elif line == "" and event_data:
                        # Empty line marks end of an event block
                        event_data = ""
