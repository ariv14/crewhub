"""A2A gateway service -- JSON-RPC 2.0 communication with external agents."""

import uuid
from typing import AsyncGenerator

import httpx
from sqlalchemy.ext.asyncio import AsyncSession


class A2AGatewayService:
    """Sends JSON-RPC 2.0 requests to remote A2A-compliant agent endpoints."""

    JSON_RPC_VERSION = "2.0"
    DEFAULT_TIMEOUT = 30.0

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
        async with httpx.AsyncClient(timeout=timeout or self.DEFAULT_TIMEOUT) as client:
            response = await client.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()

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
