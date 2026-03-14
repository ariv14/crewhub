"""Schemas for custom (community-created) agents."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CreateAgentRequest(BaseModel):
    message: str = Field(max_length=10_000, description="What kind of agent do you need?")
    category: Optional[str] = Field(None, max_length=100)
    auto_execute: bool = Field(default=True, description="Run the first task immediately")


class TryAgentRequest(BaseModel):
    message: str = Field(max_length=10_000, description="Task message for the agent")


class VoteRequest(BaseModel):
    vote: int = Field(description="+1 or -1")


class CustomAgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    category: str
    tags: list[str] | None = None
    source_query: str
    status: str
    try_count: int
    completion_count: int
    avg_rating: float
    upvote_count: int
    promoted_agent_id: str | None = None
    created_by_user_id: str | None = None
    created_at: datetime
    updated_at: datetime
    # Populated per-request for authenticated users
    user_vote: int | None = None


class CustomAgentListResponse(BaseModel):
    agents: list[CustomAgentResponse]
    total: int


class CreateAgentResponse(BaseModel):
    agent: CustomAgentResponse
    task_id: str | None = None
    task_status: str | None = None
    result: str | None = None


class AgentRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str | None
    query: str
    best_match_confidence: float | None
    custom_agent_id: str | None
    created_at: datetime


class AgentRequestListResponse(BaseModel):
    requests: list[AgentRequestResponse]
    total: int
