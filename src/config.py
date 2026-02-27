import sys

from pydantic_settings import BaseSettings


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

    # Webhook shared secret for A2A callbacks
    webhook_secret: str = ""

    # OpenAI (for embeddings — optional, uses fake embeddings if empty)
    openai_api_key: str = ""

    # Embedding settings (in-memory vector search, no Qdrant needed)
    embedding_dimension: int = 1536

    # Platform
    platform_fee_rate: float = 0.10  # 10% commission
    default_credits_bonus: float = 100.0  # New user bonus

    # Health Monitor
    health_check_interval_seconds: int = 60
    health_check_max_failures: int = 3

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Cloud Run
    port: int = 8080  # Cloud Run default port

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

# CRIT-3: Fail loudly if running with the default secret key outside of testing
_IN_TESTS = "pytest" in sys.modules
if not _IN_TESTS and settings.secret_key == "dev-secret-key-change-in-production":
    if settings.firebase_credentials_json or settings.firebase_project_id:
        print(
            "FATAL: SECRET_KEY is set to the default value while Firebase is configured. "
            "Set a strong SECRET_KEY environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)
