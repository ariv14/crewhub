# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Schemas for MCP server registry and grant management."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MCPServerCreate(BaseModel):
    name: str = Field(max_length=255)
    url: str = Field(max_length=2048)
    description: Optional[str] = None
    auth_type: str = Field(default="none", max_length=50)  # none, bearer, api_key
    auth_config: dict = Field(default_factory=dict)  # {"token": "...", "header": "..."}
    is_public: bool = False


class MCPServerUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    auth_type: Optional[str] = Field(None, max_length=50)
    auth_config: Optional[dict] = None
    is_public: Optional[bool] = None


class MCPServerResponse(BaseModel):
    id: UUID
    owner_id: UUID
    name: str
    url: str
    description: Optional[str]
    auth_type: str
    tools_cached: Optional[dict]
    is_public: bool
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MCPServerListResponse(BaseModel):
    servers: list[MCPServerResponse]
    total: int


class MCPGrantCreate(BaseModel):
    agent_id: UUID
    mcp_server_id: UUID
    scopes: list[str] = Field(default_factory=list)  # Empty = all tools
    expires_at: Optional[datetime] = None


class MCPGrantResponse(BaseModel):
    id: UUID
    user_id: UUID
    agent_id: UUID
    mcp_server_id: UUID
    scopes: list[str]
    expires_at: Optional[datetime]
    created_at: datetime
    server_name: Optional[str] = None  # Enriched in API

    model_config = {"from_attributes": True}


class MCPGrantListResponse(BaseModel):
    grants: list[MCPGrantResponse]
    total: int


class MCPToolResponse(BaseModel):
    """A tool discovered on an MCP server."""
    name: str
    description: Optional[str] = None
    parameters: Optional[dict] = None
