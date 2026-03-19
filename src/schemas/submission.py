# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Pydantic schemas for agent submissions."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SubmissionCreate(BaseModel):
    langflow_flow_id: str = Field(..., max_length=200)
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    category: str = Field(default="general", max_length=50)
    credits: float = Field(default=10, ge=5)
    tags: list[str] = Field(default_factory=list)


class SubmissionResponse(BaseModel):
    id: UUID
    user_id: UUID
    langflow_flow_id: str
    name: str
    description: Optional[str]
    category: Optional[str]
    credits: float
    tags: list[str]
    status: str
    reviewer_notes: Optional[str]
    agent_id: Optional[UUID]
    created_at: datetime
    reviewed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class SubmissionListResponse(BaseModel):
    submissions: list[SubmissionResponse]
    total: int


class SubmissionReject(BaseModel):
    notes: str = Field(..., min_length=1, max_length=1000)
