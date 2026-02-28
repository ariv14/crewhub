import ipaddress
from enum import Enum
from urllib.parse import urlparse
from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AgentStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"


class VerificationLevel(str, Enum):
    unverified = "unverified"
    namespace = "namespace"
    quality = "quality"
    audit = "audit"


# ---------------------------------------------------------------------------
# License types
# ---------------------------------------------------------------------------


class LicenseType(str, Enum):
    """How the agent is licensed on the marketplace."""

    open = "open"                  # Free, no restrictions
    freemium = "freemium"          # Free tier with paid upgrades
    commercial = "commercial"      # Paid per-use or subscription
    subscription = "subscription"  # Recurring access fee
    trial = "trial"                # Time-limited free access


class BillingModel(str, Enum):
    """How credits are calculated for each task."""

    per_task = "per_task"          # Fixed credits per task
    per_token = "per_token"        # Credits based on token usage
    per_minute = "per_minute"      # Credits based on processing time
    tiered = "tiered"              # Different rate per tier


# ---------------------------------------------------------------------------
# Pricing tier (agents can define multiple tiers)
# ---------------------------------------------------------------------------


class UsageQuota(BaseModel):
    """Usage limits for a pricing tier."""

    daily_tasks: Optional[int] = Field(None, ge=0, description="Max tasks per day (null=unlimited)")
    monthly_tasks: Optional[int] = Field(None, ge=0, description="Max tasks per month (null=unlimited)")
    max_tokens_per_task: Optional[int] = Field(None, ge=0, description="Max input tokens per task")
    rate_limit_rpm: Optional[int] = Field(None, ge=0, description="Requests per minute")


class PricingTier(BaseModel):
    """A single pricing tier for an agent."""

    name: str = Field(max_length=50)             # e.g. "free", "pro", "enterprise"
    billing_model: BillingModel = BillingModel.per_task
    credits_per_unit: float = Field(ge=0)        # Cost per task/token/minute
    monthly_fee: float = Field(0, ge=0)          # Recurring subscription fee (0 = none)
    quota: Optional[UsageQuota] = None
    features: list[str] = Field(default=[], max_length=20)  # e.g. ["priority_queue", "sla_guarantee"]
    is_default: bool = False                     # Applied when no tier is selected


class PricingModel(BaseModel):
    """Complete pricing and licensing configuration for an agent."""

    license_type: LicenseType = LicenseType.commercial
    tiers: list[PricingTier] = Field(default=[], max_length=10)

    # Legacy / simple mode — used when tiers is empty
    model: str = Field("per_task", max_length=50)
    credits: float = Field(0, ge=0)

    # Trial settings
    trial_days: Optional[int] = Field(None, ge=1, le=365)
    trial_task_limit: Optional[int] = Field(None, ge=1)

    @field_validator("tiers")
    @classmethod
    def at_most_one_default(cls, v: list[PricingTier]) -> list[PricingTier]:
        defaults = [t for t in v if t.is_default]
        if len(defaults) > 1:
            raise ValueError("Only one tier can be marked as default")
        return v

    def get_default_tier(self) -> PricingTier | None:
        """Return the default tier, or the first tier, or None."""
        for t in self.tiers:
            if t.is_default:
                return t
        return self.tiers[0] if self.tiers else None

    def get_tier(self, name: str) -> PricingTier | None:
        """Look up a tier by name."""
        for t in self.tiers:
            if t.name.lower() == name.lower():
                return t
        return None


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


def _validate_public_url(url: str, *, allow_debug_bypass: bool = True) -> str:
    """Reject private/internal IPs to prevent SSRF.

    In DEBUG mode, localhost/private addresses are allowed so that demo
    agents running on local ports can be registered.

    Set ``allow_debug_bypass=False`` for URLs that must always be validated
    (e.g. push notification callbacks).
    """
    from src.config import settings

    debug = settings.debug

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Endpoint must use http or https")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Endpoint must include a hostname")

    # In debug mode, allow localhost for local demo agents
    if debug and allow_debug_bypass:
        return url

    # Block known internal hostnames
    blocked = {"localhost", "127.0.0.1", "0.0.0.0", "[::1]", "metadata.google.internal"}
    if hostname.lower() in blocked:
        raise ValueError("Endpoint must not point to a local/internal address")
    # Block private IP ranges
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        # Not an IP literal — it's a hostname, check for internal domains
        if hostname.endswith(".internal") or hostname.endswith(".local"):
            raise ValueError("Endpoint must not point to an internal hostname")
    else:
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("Endpoint must not point to a private IP address")
    return url


VALID_EMBEDDING_PROVIDERS = {"openai", "gemini", "anthropic", "cohere", "ollama"}


class EmbeddingConfig(BaseModel):
    """Agent-level embedding override. Omit to use the platform default."""

    provider: str = Field(max_length=20)
    model: str = Field("", max_length=100)

    @field_validator("provider")
    @classmethod
    def provider_must_be_valid(cls, v: str) -> str:
        if v.lower() not in VALID_EMBEDDING_PROVIDERS:
            raise ValueError(
                f"Invalid provider '{v}'. Must be one of: {', '.join(sorted(VALID_EMBEDDING_PROVIDERS))}"
            )
        return v.lower()


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
    embedding_config: Optional[EmbeddingConfig] = None
    accepted_payment_methods: list[str] = Field(
        default=["credits"], max_length=5,
        description="Payment methods this agent accepts: credits, x402"
    )
    mcp_server_url: Optional[str] = Field(None, max_length=2048, description="MCP server URL if agent exposes MCP")
    avatar_url: Optional[str] = Field(None, max_length=2048, description="Avatar image URL")
    conversation_starters: list[str] = Field(default=[], max_length=10, description="Suggested prompts for trying the agent")
    test_cases: list[dict] = Field(default=[], max_length=20, description="Test cases for validation")

    @field_validator("avatar_url")
    @classmethod
    def avatar_url_must_be_http(cls, v: str | None) -> str | None:
        if v is not None:
            parsed = urlparse(v)
            if parsed.scheme not in ("http", "https"):
                raise ValueError("Avatar URL must use http or https")
        return v

    @field_validator("accepted_payment_methods")
    @classmethod
    def validate_payment_methods(cls, v: list[str]) -> list[str]:
        allowed = {"credits", "x402"}
        invalid = set(v) - allowed
        if invalid:
            raise ValueError(f"Invalid payment methods: {invalid}. Allowed: {allowed}")
        return v

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
    embedding_config: Optional[EmbeddingConfig] = None
    accepted_payment_methods: Optional[list[str]] = None
    mcp_server_url: Optional[str] = Field(None, max_length=2048)
    avatar_url: Optional[str] = Field(None, max_length=2048)
    conversation_starters: Optional[list[str]] = None
    test_cases: Optional[list[dict]] = None

    @field_validator("avatar_url")
    @classmethod
    def avatar_url_must_be_http(cls, v: str | None) -> str | None:
        if v is not None:
            parsed = urlparse(v)
            if parsed.scheme not in ("http", "https"):
                raise ValueError("Avatar URL must use http or https")
        return v

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
    license_type: LicenseType = LicenseType.commercial
    sla: Optional[SLADefinition] = None
    embedding_config: Optional[EmbeddingConfig] = None

    accepted_payment_methods: list[str] = ["credits"]
    mcp_server_url: Optional[str] = None
    avatar_url: Optional[str] = None
    conversation_starters: list[str] = []
    test_cases: list[dict] = []
    did: Optional[str] = None

    @field_validator("accepted_payment_methods", mode="before")
    @classmethod
    def ensure_payment_methods_list(cls, v):
        if not v:
            return ["credits"]
        return v

    @field_validator("embedding_config", mode="before")
    @classmethod
    def empty_dict_to_none(cls, v):
        if v == {} or v is None:
            return None
        return v

    @field_validator("pricing", mode="before")
    @classmethod
    def ensure_pricing_has_defaults(cls, v):
        """Ensure legacy pricing dicts get defaults for new fields."""
        if isinstance(v, dict):
            v.setdefault("license_type", "commercial")
            v.setdefault("tiers", [])
            v.setdefault("model", "per_task")
            v.setdefault("credits", 0)
        return v

    status: AgentStatus
    verification_level: VerificationLevel
    reputation_score: float
    total_tasks_completed: int
    success_rate: float
    avg_latency_ms: float
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def compute_did(self):
        """Populate the DID field from the agent ID if it has a DID public key."""
        if self.did is None and self.id:
            self.did = f"did:wba:api.aidigitalcrew.com:agents:{self.id}"
        return self


class AgentListResponse(BaseModel):
    agents: list[AgentResponse]
    total: int
    page: int
    per_page: int


class DailyTaskCount(BaseModel):
    date: str
    count: int


class AgentStatsResponse(BaseModel):
    daily_tasks: list[DailyTaskCount]


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
