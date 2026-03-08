"""Pydantic schemas for AgentCrew CRUD and execution."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.agent import AgentResponse, SkillResponse


# ---------------------------------------------------------------------------
# Member schemas
# ---------------------------------------------------------------------------


class CrewMemberCreate(BaseModel):
    agent_id: UUID
    skill_id: UUID
    position: int = Field(0, ge=0)


class CrewMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: UUID
    skill_id: UUID
    position: int
    agent: AgentResponse
    skill: SkillResponse


# ---------------------------------------------------------------------------
# Crew schemas
# ---------------------------------------------------------------------------


class CrewCreate(BaseModel):
    name: str = Field(max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    icon: str = Field("🤖", max_length=10)
    is_public: bool = False
    members: list[CrewMemberCreate] = Field(default=[], max_length=20)


class CrewUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    icon: Optional[str] = Field(None, max_length=10)
    is_public: Optional[bool] = None
    members: Optional[list[CrewMemberCreate]] = None


class CrewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    name: str
    description: Optional[str]
    icon: str
    is_public: bool
    members: list[CrewMemberResponse]
    created_at: datetime
    updated_at: datetime


class CrewListResponse(BaseModel):
    crews: list[CrewResponse]
    total: int


# ---------------------------------------------------------------------------
# Run / Clone
# ---------------------------------------------------------------------------


class CrewRunRequest(BaseModel):
    message: str = Field(max_length=10000)


class CrewRunResponse(BaseModel):
    crew_id: UUID
    task_ids: list[UUID]
    member_task_map: dict[str, str]  # agent_id -> task_id
