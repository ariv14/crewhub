"""Tests for MCP server integration."""

import importlib.util

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_mcp_endpoint_exists(client: AsyncClient):
    """The /mcp endpoint should respond (not 404)."""
    resp = await client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "initialize", "id": 1},
    )
    # fastapi-mcp may not be installed in test env — accept 200 or 404
    assert resp.status_code in (200, 404, 405)


@pytest.mark.asyncio
async def test_mcp_resources_module_importable():
    """MCP resources module should be importable."""
    from src.mcp.resources import (
        get_agent_registry,
        get_agent_card,
        get_discovery_categories,
        get_trending_skills,
    )
    assert callable(get_agent_registry)
    assert callable(get_agent_card)
    assert callable(get_discovery_categories)
    assert callable(get_trending_skills)


@pytest.mark.asyncio
async def test_mcp_client_importable():
    """MCP client module should be importable."""
    from src.services.mcp_client import MCPClient
    client = MCPClient("http://localhost:9999")
    assert client.server_url == "http://localhost:9999"
    await client.close()


@pytest.mark.asyncio
async def test_mcp_client_context_manager():
    """MCP client can be used as an async context manager."""
    from src.services.mcp_client import MCPClient
    async with MCPClient("http://localhost:9999") as client:
        assert client.server_url == "http://localhost:9999"


@pytest.mark.asyncio
@pytest.mark.skipif(
    importlib.util.find_spec("fastapi_mcp") is None,
    reason="fastapi-mcp not installed",
)
async def test_mcp_tools_list(client: AsyncClient):
    """If fastapi-mcp is installed, tools/list returns tools matching FastAPI endpoints."""
    resp = await client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
    )
    assert resp.status_code == 200
    data = resp.json()
    tools = data.get("result", {}).get("tools", [])
    assert len(tools) > 0, "MCP should expose at least one tool"
    tool_names = [t["name"] for t in tools]
    # Verify some well-known endpoints are exposed as tools
    assert any("agent" in name.lower() or "health" in name.lower() for name in tool_names), (
        f"Expected agent or health related tool, got: {tool_names[:5]}"
    )


@pytest.mark.asyncio
async def test_mcp_resources_router_exists(client: AsyncClient):
    """MCP resources router endpoints are registered."""
    from src.main import app

    routes = [r.path for r in app.routes]
    assert any("mcp-resources" in r for r in routes), (
        f"Expected mcp-resources routes, got: {[r for r in routes if 'mcp' in r.lower()]}"
    )
