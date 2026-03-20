# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
import logging
import os
import sys

from pydantic_settings import BaseSettings

_config_logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Application
    app_name: str = "CrewHub"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Database (Neon PostgreSQL free tier)
    database_url: str = "postgresql+asyncpg://crewhub:crewhub@localhost:5432/crewhub"

    # Firebase Auth
    firebase_credentials_json: str = ""  # Path to service account JSON, or JSON string
    firebase_project_id: str = ""

    # Auth — MUST be overridden via SECRET_KEY env var in production
    secret_key: str = "dev-secret-key-change-in-production"
    # Separate encryption key for stored secrets (falls back to secret_key if empty)
    encryption_key: str = ""
    # Privacy consent version — bump when privacy policy changes materially
    consent_version: str = "v1.0"

    # Webhook shared secret for A2A callbacks
    webhook_secret: str = ""

    # Embedding provider: "openai", "gemini", "anthropic", "cohere", "ollama"
    # Users must provide their own API key via Settings > LLM Keys (BYOK).
    # Ollama runs locally and requires no key.
    embedding_provider: str = "openai"
    ollama_base_url: str = "http://localhost:11434"  # Local Ollama

    # Embedding model overrides (sensible defaults per provider)
    embedding_model: str = ""  # Empty = use provider default

    # Embedding dimension (must match the chosen model)
    embedding_dimension: int = 1536

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # Stripe credit pack Price IDs (one-time products)
    # Format: "credits:price_id,credits:price_id,..."
    stripe_credit_packs: str = ""  # e.g. "500:price_xxx,2000:price_yyy,5000:price_zzz,10000:price_www"

    # Frontend URL for Stripe redirect callbacks
    frontend_url: str = "http://localhost:3000"

    # Payouts (Stripe Connect)
    payout_minimum_credits: float = 2500.0   # $25 minimum withdrawal
    payout_clearance_days: int = 7           # days after task completion before credits are withdrawable
    credit_to_usd_rate: float = 0.01         # 1 credit = $0.01 USD

    # Platform
    platform_fee_rate: float = 0.10  # 10% commission
    default_credits_bonus: float = 250.0  # New user bonus

    # Health Monitor
    health_check_interval_seconds: int = 60
    health_check_max_failures: int = 12

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # x402 Payment
    x402_facilitator_url: str = ""
    x402_supported_chains: str = "base"
    x402_supported_tokens: str = "USDC"
    x402_receipt_timeout_minutes: int = 10

    # Platform-owned embedding API key (used when no user BYOK key is available).
    # Enables search, suggestions, and skill registration without user keys.
    platform_embedding_key: str = ""

    # Circuit Breaker
    circuit_breaker_threshold: int = 5  # failures before opening circuit
    circuit_breaker_window_seconds: int = 3600  # 1 hour window

    # Per-User Spending Limits
    default_daily_spend_limit: float = 0  # 0 = unlimited

    # High-Cost Task Approval
    high_cost_approval_threshold: float = 50.0  # credits above this require confirmation

    # Task Cancellation Grace Period
    task_grace_period_seconds: int = 5  # seconds before dispatch

    # Eval (LLM-as-judge quality scoring)
    eval_enabled: bool = True
    eval_llm_model: str = "gemini/gemini-2.0-flash"

    # Content Moderation
    content_moderation_enabled: bool = True
    content_moderation_level: int = 1  # 1=regex, 2=OpenAI moderation API

    # Abuse Detection
    abuse_detection_enabled: bool = True
    abuse_max_tasks_per_minute: int = 20

    # Delegation
    max_delegation_depth: int = 3

    # Custom Agent Creator
    creator_agent_id: str = ""       # UUID of the registered Creator Agent
    creator_skill_id: str = ""       # UUID of the "custom-execute" skill
    custom_agent_create_cost: float = 5.0   # Credits to create a custom agent
    custom_agent_try_cost: float = 3.0      # Credits to try a community agent
    custom_agent_daily_limit: int = 5       # Max creations per user per day

    # Telemetry
    telemetry_enabled: bool = True
    discord_feedback_webhook: str = ""

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "text"

    # Security
    force_https: bool = False

    # Cloud Run
    port: int = 8080  # Cloud Run default port

    model_config = {"env_file": ".env", "extra": "ignore"}

    def warn_insecure_defaults(self) -> None:
        """Log warnings for configuration values that are unsafe in production."""
        if "change" in self.secret_key.lower() or len(self.secret_key) < 32:
            _config_logger.warning(
                "SECRET_KEY appears to be a default — change for production"
            )
        if self.debug:
            _config_logger.warning("DEBUG mode is ON — disable for production")
        if "sqlite" in self.database_url:
            _config_logger.warning(
                "Using SQLite — use PostgreSQL for production"
            )


settings = Settings()

# Auto-enable HTTPS in production — but NOT on HF Spaces (reverse proxy handles SSL)
_on_hf_spaces = bool(os.environ.get("SPACE_ID") or os.environ.get("SPACE_HOST"))
if not settings.debug and "postgresql" in settings.database_url and not settings.force_https and not _on_hf_spaces:
    settings.force_https = True
    _config_logger.info("Auto-enabled force_https for production deployment")

# CRIT-3: Fail loudly if running with the default secret key outside of testing
_IN_TESTS = "pytest" in sys.modules
_DEFAULT_SECRET = "dev-secret-key-change-in-production"
if not _IN_TESTS and settings.secret_key == _DEFAULT_SECRET:
    if not settings.debug:
        print(
            "FATAL: SECRET_KEY is set to the default value in production mode. "
            "Set a strong SECRET_KEY environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)
    elif settings.firebase_credentials_json or settings.firebase_project_id:
        print(
            "FATAL: SECRET_KEY is set to the default value while Firebase is configured. "
            "Set a strong SECRET_KEY environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)

# CRIT-SEC: Fail if STRIPE_WEBHOOK_SECRET is unset when Stripe is configured
if not _IN_TESTS and not settings.debug and settings.stripe_secret_key and not settings.stripe_webhook_secret:
    print(
        "FATAL: STRIPE_WEBHOOK_SECRET is not set but STRIPE_SECRET_KEY is configured. "
        "Stripe webhooks will fail and subscription state will not update. "
        "Set the STRIPE_WEBHOOK_SECRET environment variable.",
        file=sys.stderr,
    )
    sys.exit(1)

# CRIT-SEC: Fail if WEBHOOK_SECRET is unset in production mode
if not _IN_TESTS and not settings.debug and not settings.webhook_secret:
    print(
        "FATAL: WEBHOOK_SECRET is not set in production mode. "
        "Without it, webhook endpoints accept unauthenticated requests. "
        "Set the WEBHOOK_SECRET environment variable.",
        file=sys.stderr,
    )
    sys.exit(1)

# WARN: Redis strongly recommended in production for shared rate limiting
if not _IN_TESTS and not settings.debug and not os.environ.get("REDIS_URL"):
    print(
        "WARNING: REDIS_URL is not set in production mode. "
        "Rate limiting will use in-memory state (not shared across workers). "
        "Set REDIS_URL for production-grade rate limiting.",
        file=sys.stderr,
    )

# CRIT-SEC: Validate DATABASE_URL is PostgreSQL in production
if not _IN_TESTS and not settings.debug and "sqlite" in settings.database_url:
    print(
        "FATAL: SQLite is not supported in production mode. "
        "Set DATABASE_URL to a PostgreSQL connection string.",
        file=sys.stderr,
    )
    sys.exit(1)
