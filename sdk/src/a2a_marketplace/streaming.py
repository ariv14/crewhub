"""Async streaming support for task updates via WebSocket."""

from __future__ import annotations

import json
from typing import AsyncIterator

import websockets
import websockets.asyncio.client

from .models import Task


class TaskStream:
    """Async iterator for streaming task updates via WebSocket.

    Usage::

        stream = TaskStream(base_url="http://localhost:8000/api/v1",
                            task_id="task-123",
                            api_key="key")
        async for task in stream:
            print(task.status)
    """

    def __init__(self, base_url: str, task_id: str, api_key: str) -> None:
        self._task_id = task_id
        self._api_key = api_key

        # Convert http(s):// to ws(s):// for the WebSocket URL.
        ws_url = base_url.replace("https://", "wss://").replace(
            "http://", "ws://"
        )
        self._ws_url = f"{ws_url}/tasks/{task_id}/stream"
        self._connection: websockets.asyncio.client.ClientConnection | None = (
            None
        )

    async def _connect(self) -> None:
        """Establish the WebSocket connection with auth headers."""
        extra_headers = {"X-API-Key": self._api_key}
        self._connection = await websockets.asyncio.client.connect(
            self._ws_url, additional_headers=extra_headers
        )

    async def close(self) -> None:
        """Close the WebSocket connection if open."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    def __aiter__(self) -> AsyncIterator[Task]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[Task]:
        """Yield Task model instances from each WebSocket message."""
        if self._connection is None:
            await self._connect()

        assert self._connection is not None

        try:
            async for raw_message in self._connection:
                if isinstance(raw_message, bytes):
                    raw_message = raw_message.decode("utf-8")

                data = json.loads(raw_message)
                yield Task.model_validate(data)
        finally:
            await self.close()
