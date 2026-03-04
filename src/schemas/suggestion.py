"""Schemas for task delegation suggestions."""

from typing import Optional

from pydantic import BaseModel, Field

from src.schemas.agent import AgentResponse, SkillResponse


class SuggestionRequest(BaseModel):
    message: str = Field(max_length=10_000)
    category: Optional[str] = Field(None, max_length=100)
    tags: list[str] = Field(default=[], max_length=20)
    max_credits: Optional[float] = Field(None, ge=0)
    limit: int = Field(default=3, ge=1, le=10)


class SkillSuggestion(BaseModel):
    agent: AgentResponse
    skill: SkillResponse
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    low_confidence: bool = False


class SuggestionResponse(BaseModel):
    suggestions: list[SkillSuggestion]
    fallback_used: bool = False
    hint: Optional[str] = None
