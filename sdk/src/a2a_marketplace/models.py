"""Pydantic models for the A2A Marketplace SDK."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Skill(BaseModel):
    """A skill offered by an agent."""

    id: str
    skill_key: str
    name: str
    description: str
    input_modes: list[str] = Field(default_factory=list)
    output_modes: list[str] = Field(default_factory=list)


class Agent(BaseModel):
    """An agent registered in the marketplace."""

    id: str
    name: str
    description: str
    endpoint: str
    version: str = "1.0.0"
    category: str = ""
    tags: list[str] = Field(default_factory=list)
    pricing: dict = Field(default_factory=dict)
    reputation_score: float = 0.0
    success_rate: float = 0.0
    skills: list[Skill] = Field(default_factory=list)


class Task(BaseModel):
    """A task delegated from one agent to another."""

    id: str
    client_agent_id: str
    provider_agent_id: str
    skill_id: str
    status: str
    messages: list[dict] = Field(default_factory=list)
    artifacts: list[dict] = Field(default_factory=list)
    credits_quoted: float = 0.0
    credits_charged: float = 0.0
    created_at: str = ""


class SearchResult(BaseModel):
    """A single result from agent discovery."""

    agent: Agent
    relevance_score: float
    match_reason: str = ""


class Balance(BaseModel):
    """Credit balance for the authenticated account."""

    balance: float
    reserved: float
    available: float
    currency: str = "credits"


class Transaction(BaseModel):
    """A credit transaction record."""

    id: str
    amount: float
    type: str
    description: str
    created_at: str = ""
