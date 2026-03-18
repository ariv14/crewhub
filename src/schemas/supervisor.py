# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Pydantic schemas for supervisor planning."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# --- Plan Request ---

class SupervisorPlanRequest(BaseModel):
    goal: str = Field(min_length=10, max_length=2000)
    llm_provider: Optional[str] = None
    max_credits: Optional[float] = Field(None, ge=1)


# --- Plan Steps & Response ---

class SupervisorPlanStep(BaseModel):
    agent_id: UUID
    skill_id: UUID
    agent_name: str
    skill_name: str
    step_group: int = Field(ge=0)
    input_mode: str = Field("chain", pattern=r"^(chain|original|custom)$")
    input_template: Optional[str] = None
    instructions: Optional[str] = Field(None, max_length=1000)
    label: Optional[str] = Field(None, max_length=255)
    confidence: float = Field(ge=0, le=1)
    estimated_credits: float = Field(ge=0)
    sub_steps: Optional[list[dict]] = None  # Avoids self-referencing schema (fastapi_mcp recursion)


class SupervisorPlan(BaseModel):
    name: str
    description: str
    steps: list[SupervisorPlanStep]
    total_estimated_credits: float
    llm_provider_used: str
    plan_id: str


# --- Replan & Approve ---

class ReplanRequest(BaseModel):
    goal: str = Field(min_length=10, max_length=2000)
    feedback: str = Field(min_length=5, max_length=1000)
    previous_plan_id: str


class ApprovePlanRequest(BaseModel):
    plan_id: str
    workflow_name: Optional[str] = Field(None, max_length=255)
