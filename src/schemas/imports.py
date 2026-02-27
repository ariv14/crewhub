"""Schemas for skill import from external registries."""

import re
from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from src.schemas.agent import PricingModel


ALLOWED_IMPORT_DOMAINS = {
    "clawhub.io",
    "github.com",
    "raw.githubusercontent.com",
    "clawmart.online",
}

# GitHub URLs must be scoped to the openclaw org per design spec
GITHUB_ALLOWED_PATH_PREFIXES = {
    "github.com": "/openclaw/",
    "raw.githubusercontent.com": "/openclaw/",
}


class OpenClawImportRequest(BaseModel):
    """Request to import an OpenClaw skill as a CrewHub agent."""

    skill_url: str = Field(max_length=500, description="ClawHub or ClawMart skill URL")
    pricing: PricingModel
    category: str = Field("general", max_length=100)
    tags: list[str] = Field(default=["imported", "openclaw"], max_length=20)

    @field_validator("skill_url")
    @classmethod
    def url_must_be_allowed(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("URL must use http or https")
        hostname = parsed.hostname or ""
        if not any(hostname == d or hostname.endswith(f".{d}") for d in ALLOWED_IMPORT_DOMAINS):
            raise ValueError(
                f"URL domain '{hostname}' not in allowed list: {', '.join(sorted(ALLOWED_IMPORT_DOMAINS))}"
            )
        # GitHub/raw.githubusercontent.com must be scoped to openclaw org
        required_prefix = GITHUB_ALLOWED_PATH_PREFIXES.get(hostname)
        if required_prefix and not (parsed.path or "").startswith(required_prefix):
            raise ValueError(
                f"Only {hostname}{required_prefix}* URLs are allowed"
            )
        return v


class OpenClawImportResponse(BaseModel):
    """Response after importing an OpenClaw skill."""

    agent_id: str
    name: str
    status: str
    source: str = "openclaw"
    source_url: str
    message: str = "Imported successfully. Agent starts as inactive — activate manually after review."
