"""Schemas for the agent detection / auto-discovery endpoint."""

from pydantic import BaseModel, Field, field_validator

from src.schemas.agent import _validate_public_url


class DetectRequest(BaseModel):
    url: str = Field(max_length=500)

    @field_validator("url")
    @classmethod
    def url_must_be_public(cls, v: str) -> str:
        return _validate_public_url(v)


class DetectedSkill(BaseModel):
    skill_key: str
    name: str
    description: str
    input_modes: list[str] = ["text"]
    output_modes: list[str] = ["text"]


class DetectResponse(BaseModel):
    name: str
    description: str
    url: str
    version: str
    capabilities: dict = {}
    skills: list[DetectedSkill] = []
    suggested_registration: dict  # AgentCreate-compatible payload
    card_url: str
    warnings: list[str] = []
