"""FastAPI router exposing MCP resources as discoverable endpoints.

By making these regular FastAPI endpoints, fastapi-mcp will automatically
generate MCP tools for them when mounted.
"""

from fastapi import APIRouter

from src.mcp.resources import (
    get_agent_card,
    get_agent_registry,
    get_discovery_categories,
    get_trending_skills,
)

router = APIRouter(prefix="/mcp-resources", tags=["mcp-resources"])


@router.get("/registry", summary="List all active agents (MCP resource)")
async def mcp_agent_registry():
    """agents://registry — list of all active agents with key metadata."""
    return await get_agent_registry()


@router.get("/agents/{agent_id}/card", summary="Get agent card (MCP resource)")
async def mcp_agent_card(agent_id: str):
    """agents://{id}/card — A2A agent card for a specific agent."""
    return await get_agent_card(agent_id)


@router.get("/categories", summary="List agent categories (MCP resource)")
async def mcp_discovery_categories():
    """discovery://categories — available agent categories with counts."""
    return await get_discovery_categories()


@router.get("/trending", summary="Trending skills (MCP resource)")
async def mcp_trending_skills():
    """discovery://trending — skills with most completed tasks."""
    return await get_trending_skills()
