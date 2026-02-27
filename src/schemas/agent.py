import ipaddress
from enum import Enum
from urllib.parse import urlparse
from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"


class VerificationLevel(str, Enum):
    unverified = "unverified"
    namespace = "namespace"
    quality = "quality"
    audit = "audit"


class PricingModel(BaseModel):
    model: str = Field(max_length=50)  # per_task, per_token, flat
    credits: float = Field(ge=0)


class SLADefinition(BaseModel):
    max_latency_ms: Optional[int] = Field(None, ge=0)
    uptime_guarantee: Optional[float] = Field(None, ge=0, le=100)


class SkillExample(BaseModel):
    input: str = Field(max_length=5000)
    output: str = Field(max_length=5000)
    description: Optional[str] = Field(None, max_length=1000)


class SkillCreate(BaseModel):
    skill_key: str = Field(max_length=100)
    name: str = Field(max_length=255)
    description: str = Field(max_length=5000)
    input_modes: list[str] = Field(max_length=10)
    output_modes: list[str] = Field(max_length=10)
    examples: list[SkillExample] = Field(default=[], max_length=20)
    avg_credits: float = Field(0, ge=0)
    avg_latency_ms: int = Field(0, ge=0)


class SkillResponse(SkillCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


def _validate_public_url(url: str) -> str:
    """Reject private/internal IPs to prevent SSRF."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Endpoint must use http or https")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Endpoint must include a hostname")
    # Block known internal hostnames
    blocked = {"localhost", "127.0.0.1", "0.0.0.0", "[::1]", "metadata.google.internal"}
    if hostname.lower() in blocked:
        raise ValueError("Endpoint must not point to a local/internal address")
    # Block private IP ranges
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("Endpoint must not point to a private IP address")
    except ValueError:
        # Not an IP literal — it's a hostname, which is fine
        if hostname.endswith(".internal") or hostname.endswith(".local"):
            raise ValueError("Endpoint must not point to an internal hostname")
    return url


class AgentCreate(BaseModel):
    name: str = Field(max_length=255)
    description: str = Field(max_length=10000)
    version: str = Field("1.0.0", max_length=50)
    endpoint: str = Field(max_length=500)
    capabilities: dict = {}
    skills: list[SkillCreate] = Field(default=[], max_length=50)
    security_schemes: list[dict] = Field(default=[], max_length=10)
    category: str = Field("general", max_length=100)
    tags: list[str] = Field(default=[], max_length=20)
    pricing: PricingModel
    sla: Optional[SLADefinition] = None

    @field_validator("endpoint")
    @classmethod
    def endpoint_must_be_public(cls, v: str) -> str:
        return _validate_public_url(v)


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=10000)
    version: Optional[str] = Field(None, max_length=50)
    endpoint: Optional[str] = Field(None, max_length=500)
    capabilities: Optional[dict] = None
    skills: Optional[list[SkillCreate]] = None
    security_schemes: Optional[list[dict]] = None
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[list[str]] = None
    pricing: Optional[PricingModel] = None
    sla: Optional[SLADefinition] = None

    @field_validator("endpoint")
    @classmethod
    def endpoint_must_be_public(cls, v: str | None) -> str | None:
        if v is not None:
            return _validate_public_url(v)
        return v


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    name: str
    description: str
    version: str
    endpoint: str
    capabilities: dict
    skills: list[SkillResponse]
    security_schemes: list[dict]
    category: str
    tags: list[str]
    pricing: PricingModel
    sla: Optional[SLADefinition] = None
    status: AgentStatus
    verification_level: VerificationLevel
    reputation_score: float
    total_tasks_completed: int
    success_rate: float
    avg_latency_ms: float
    created_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    agents: list[AgentResponse]
    total: int
    page: int
    per_page: int


class AgentCardResponse(BaseModel):
    """A2A spec compliant agent card."""
    name: str
    description: str
    url: str
    version: str
    capabilities: dict
    skills: list[dict]
    securitySchemes: list[dict]
    defaultInputModes: list[str]
    defaultOutputModes: list[str]
