"""MCP client for calling external MCP servers.

Allows CrewHub agents to discover and invoke tools on external MCP-compatible
servers via SSE transport.
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

MCP_TIMEOUT = 30  # seconds


class MCPClient:
    """Client for interacting with external MCP servers.

    Reuses a single httpx.AsyncClient for connection pooling across calls.
    Call close() when done, or use as an async context manager.
    """

    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip("/")
        self._tools: list[dict] | None = None
        self._client = httpx.AsyncClient(timeout=MCP_TIMEOUT)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def list_tools(self) -> list[dict]:
        """Discover available tools on the remote MCP server."""
        if self._tools is not None:
            return self._tools

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1,
        }
        try:
            resp = await self._client.post(
                self.server_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
            self._tools = data.get("result", {}).get("tools", [])
            return self._tools
        except Exception as e:
            logger.error(f"MCP list_tools failed for {self.server_url}: {e}")
            return []

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        """Invoke a tool on the remote MCP server and return the result."""
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments or {},
            },
            "id": 2,
        }
        try:
            resp = await self._client.post(
                self.server_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
            if "error" in data and data["error"]:
                logger.error(f"MCP tool call error: {data['error']}")
                return {"error": data["error"]}
            return data.get("result")
        except Exception as e:
            logger.error(f"MCP call_tool '{name}' failed for {self.server_url}: {e}")
            return {"error": str(e)}

    async def health_check(self) -> bool:
        """Check if the remote MCP server is reachable."""
        try:
            resp = await self._client.get(self.server_url)
            return resp.status_code < 500
        except Exception:
            return False
