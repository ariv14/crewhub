# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Schemas for organizations, teams, and memberships."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Organization ──────────────────────────────────────────────

class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9\-]+$")
    avatar_url: str | None = None


class OrganizationUpdate(BaseModel):
    name: str | None = None
    slug: str | None = Field(None, pattern=r"^[a-z0-9\-]+$")
    avatar_url: str | None = None


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    avatar_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Team ──────────────────────────────────────────────────────

class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class TeamUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class TeamResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Membership ────────────────────────────────────────────────

class MembershipCreate(BaseModel):
    user_email: str = Field(..., description="Email of user to invite")
    role: str = Field("member", pattern=r"^(viewer|member|admin|owner)$")
    team_id: UUID | None = None


class MembershipUpdate(BaseModel):
    role: str = Field(..., pattern=r"^(viewer|member|admin|owner)$")


class MembershipResponse(BaseModel):
    id: UUID
    user_id: UUID
    organization_id: UUID
    team_id: UUID | None = None
    role: str
    created_at: datetime
    user_email: str | None = None
    user_name: str | None = None

    model_config = {"from_attributes": True}


# ── List wrappers ─────────────────────────────────────────────

class OrganizationListResponse(BaseModel):
    organizations: list[OrganizationResponse]
    total: int


class TeamListResponse(BaseModel):
    teams: list[TeamResponse]
    total: int


class MembershipListResponse(BaseModel):
    members: list[MembershipResponse]
    total: int
