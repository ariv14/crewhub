"""Tests for MCP server integration."""

import importlib.util

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_mcp_endpoint_registered(client: AsyncClient):
    """The /mcp route should be registered in the FastAPI app."""
    from src.main import app

    routes = [r.path for r in app.routes]
    if importlib.util.find_spec("fastapi_mcp") is not None:
        assert any("/mcp" == r or r.startswith("/mcp") for r in routes), (
            f"Expected /mcp route, got: {[r for r in routes if 'mcp' in r.lower()]}"
        )
    # If fastapi-mcp is not installed, the route won't exist — that's fine


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
async def test_mcp_server_has_tools():
    """FastApiMCP should discover and register tools from FastAPI endpoints."""
    from src.main import app

    # Verify the MCP server object was created and attached tools
    # mount_http() requires a lifespan-managed task group, so we can't send
    # live HTTP requests in unit tests. Instead, verify the server registered tools.
    for attr_name in dir(app):
        obj = getattr(app, attr_name, None)
        if hasattr(obj, '_tool_manager'):
            tools = obj._tool_manager
            assert tools is not None, "MCP tool manager should be initialized"
            return

    # Fallback: verify the /mcp route exists (mount_http was called)
    routes = [r.path for r in app.routes]
    assert any("/mcp" == r or r.startswith("/mcp") for r in routes), (
        f"Expected /mcp route from mount_http(), got: {routes}"
    )


@pytest.mark.asyncio
async def test_mcp_resources_router_exists(client: AsyncClient):
    """MCP resources router endpoints are registered."""
    from src.main import app

    routes = [r.path for r in app.routes]
    assert any("mcp-resources" in r for r in routes), (
        f"Expected mcp-resources routes, got: {[r for r in routes if 'mcp' in r.lower()]}"
    )
