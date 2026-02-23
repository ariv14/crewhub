from enum import Enum
from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


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
    model: str  # per_task, per_token, flat
    credits: float


class SLADefinition(BaseModel):
    max_latency_ms: Optional[int] = None
    uptime_guarantee: Optional[float] = None


class SkillExample(BaseModel):
    input: str
    output: str
    description: Optional[str] = None


class SkillCreate(BaseModel):
    skill_key: str
    name: str
    description: str
    input_modes: list[str]
    output_modes: list[str]
    examples: list[SkillExample] = []
    avg_credits: float = 0
    avg_latency_ms: int = 0


class SkillResponse(SkillCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class AgentCreate(BaseModel):
    name: str
    description: str
    version: str = "1.0.0"
    endpoint: str
    capabilities: dict = {}
    skills: list[SkillCreate] = []
    security_schemes: list[dict] = []
    category: str = "general"
    tags: list[str] = []
    pricing: PricingModel
    sla: Optional[SLADefinition] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    endpoint: Optional[str] = None
    capabilities: Optional[dict] = None
    skills: Optional[list[SkillCreate]] = None
    security_schemes: Optional[list[dict]] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    pricing: Optional[PricingModel] = None
    sla: Optional[SLADefinition] = None


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
