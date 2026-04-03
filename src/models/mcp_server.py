# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""MCP server registry and access grant models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class MCPServer(Base):
    """A registered MCP server that agents can use to access external tools."""

    __tablename__ = "mcp_servers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    auth_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="none"
    )  # none, bearer, api_key, oauth2
    auth_config: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    tools_cached: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    grants = relationship("MCPGrant", back_populates="mcp_server", cascade="all, delete-orphan")


class MCPGrant(Base):
    """Authorization for an agent to access a specific MCP server."""

    __tablename__ = "mcp_grants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mcp_server_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scopes: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )  # Tool names; empty = all tools
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    mcp_server = relationship("MCPServer", back_populates="grants")
