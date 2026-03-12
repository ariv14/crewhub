"""Schemas for the A2A compliance validation endpoint."""

from pydantic import BaseModel, Field, field_validator

from src.schemas.agent import _validate_public_url


class ValidateRequest(BaseModel):
    url: str = Field(max_length=500)

    @field_validator("url")
    @classmethod
    def url_must_be_public(cls, v: str) -> str:
        return _validate_public_url(v)


class ValidationCheck(BaseModel):
    name: str
    passed: bool
    message: str
    severity: str = "error"  # "error" | "warning" | "info"


class ValidateResponse(BaseModel):
    url: str
    valid: bool
    checks: list[ValidationCheck]
    agent_name: str | None = None
    skills_count: int = 0
    suggestions: list[str] = []
