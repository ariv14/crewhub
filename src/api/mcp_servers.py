# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""MCP server registry and grant management API."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.auth import resolve_db_user_id
from src.core.rate_limiter import rate_limit_dependency
from src.database import get_db
from src.models.mcp_server import MCPGrant, MCPServer
from src.schemas.mcp import (
    MCPGrantCreate,
    MCPGrantListResponse,
    MCPGrantResponse,
    MCPServerCreate,
    MCPServerListResponse,
    MCPServerResponse,
    MCPServerUpdate,
    MCPToolResponse,
)
from src.services.mcp_client import MCPClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp-servers", tags=["mcp-servers"])


# ---------------------------------------------------------------------------
# MCP Server CRUD
# ---------------------------------------------------------------------------


@router.get("/", response_model=MCPServerListResponse, dependencies=[Depends(rate_limit_dependency)])
async def list_mcp_servers(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
) -> MCPServerListResponse:
    """List MCP servers — user's own + public servers."""
    result = await db.execute(
        select(MCPServer)
        .where((MCPServer.owner_id == user_id) | (MCPServer.is_public == True))
        .where(MCPServer.status == "active")
        .order_by(MCPServer.created_at.desc())
    )
    servers = list(result.scalars().all())
    return MCPServerListResponse(
        servers=[MCPServerResponse.model_validate(s) for s in servers],
        total=len(servers),
    )


@router.post("/", response_model=MCPServerResponse, status_code=201, dependencies=[Depends(rate_limit_dependency)])
async def create_mcp_server(
    data: MCPServerCreate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
) -> MCPServerResponse:
    """Register a new MCP server."""
    # Validate URL is HTTPS (security)
    if not data.url.startswith("https://"):
        raise HTTPException(status_code=400, detail="MCP server URL must use HTTPS")

    server = MCPServer(
        owner_id=user_id,
        name=data.name,
        url=data.url,
        description=data.description,
        auth_type=data.auth_type,
        auth_config=data.auth_config,
        is_public=data.is_public,
    )
    db.add(server)
    await db.commit()
    await db.refresh(server)
    return MCPServerResponse.model_validate(server)


@router.get("/{server_id}", response_model=MCPServerResponse)
async def get_mcp_server(
    server_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
) -> MCPServerResponse:
    """Get MCP server details."""
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    if server.owner_id != user_id and not server.is_public:
        raise HTTPException(status_code=403, detail="Not authorized to view this server")
    return MCPServerResponse.model_validate(server)


@router.put("/{server_id}", response_model=MCPServerResponse)
async def update_mcp_server(
    server_id: UUID,
    data: MCPServerUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
) -> MCPServerResponse:
    """Update an MCP server. Requires ownership."""
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    if server.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this server")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(server, field, value)
    await db.commit()
    await db.refresh(server)
    return MCPServerResponse.model_validate(server)


@router.delete("/{server_id}", status_code=204)
async def delete_mcp_server(
    server_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
):
    """Delete an MCP server. Also removes all grants."""
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    if server.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this server")
    await db.delete(server)
    await db.commit()


@router.post("/{server_id}/refresh-tools", response_model=list[MCPToolResponse])
async def refresh_tools(
    server_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
) -> list[MCPToolResponse]:
    """Fetch and cache the list of available tools from the MCP server."""
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    if server.owner_id != user_id and not server.is_public:
        raise HTTPException(status_code=403, detail="Not authorized")

    async with MCPClient(server.url) as client:
        tools = await client.list_tools()

    server.tools_cached = {"tools": tools}
    await db.commit()

    return [
        MCPToolResponse(
            name=t.get("name", ""),
            description=t.get("description"),
            parameters=t.get("inputSchema"),
        )
        for t in tools
    ]


# ---------------------------------------------------------------------------
# MCP Grants
# ---------------------------------------------------------------------------


@router.get("/grants/", response_model=MCPGrantListResponse, dependencies=[Depends(rate_limit_dependency)])
async def list_grants(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
) -> MCPGrantListResponse:
    """List all MCP grants for the current user."""
    result = await db.execute(
        select(MCPGrant)
        .options(selectinload(MCPGrant.mcp_server))
        .where(MCPGrant.user_id == user_id)
        .order_by(MCPGrant.created_at.desc())
    )
    grants = list(result.scalars().all())
    responses = []
    for g in grants:
        resp = MCPGrantResponse.model_validate(g)
        if g.mcp_server:
            resp.server_name = g.mcp_server.name
        responses.append(resp)
    return MCPGrantListResponse(grants=responses, total=len(responses))


@router.post("/grants/", response_model=MCPGrantResponse, status_code=201, dependencies=[Depends(rate_limit_dependency)])
async def create_grant(
    data: MCPGrantCreate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
) -> MCPGrantResponse:
    """Grant an agent access to an MCP server."""
    # Verify server exists and user owns it (or it's public)
    result = await db.execute(select(MCPServer).where(MCPServer.id == data.mcp_server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    if server.owner_id != user_id and not server.is_public:
        raise HTTPException(status_code=403, detail="You don't own this MCP server")

    # Check for duplicate grant
    existing = await db.execute(
        select(MCPGrant).where(
            MCPGrant.user_id == user_id,
            MCPGrant.agent_id == data.agent_id,
            MCPGrant.mcp_server_id == data.mcp_server_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Grant already exists for this agent+server")

    grant = MCPGrant(
        user_id=user_id,
        agent_id=data.agent_id,
        mcp_server_id=data.mcp_server_id,
        scopes=data.scopes,
        expires_at=data.expires_at,
    )
    db.add(grant)
    await db.commit()
    await db.refresh(grant)

    resp = MCPGrantResponse.model_validate(grant)
    resp.server_name = server.name
    return resp


@router.delete("/grants/{grant_id}", status_code=204)
async def revoke_grant(
    grant_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
):
    """Revoke an MCP grant."""
    result = await db.execute(select(MCPGrant).where(MCPGrant.id == grant_id))
    grant = result.scalar_one_or_none()
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")
    if grant.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to revoke this grant")
    await db.delete(grant)
    await db.commit()
