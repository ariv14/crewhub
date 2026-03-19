# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, text

from src.config import settings
from src.core.embeddings import MissingAPIKeyError
from src.core.exceptions import MarketplaceError
from src.core.logging import setup_logging
from src.database import engine
from src.middleware.request_id import RequestTracingMiddleware

logger = logging.getLogger(__name__)


async def _health_monitor_loop(interval: int = 300) -> None:
    """Periodically check all active agents' health every `interval` seconds."""
    from src.database import async_session
    from src.services.health_monitor import HealthMonitorService

    while True:
        try:
            await asyncio.sleep(interval)
            async with async_session() as db:
                service = HealthMonitorService(db)
                results = await service.check_all_active_agents()
                healthy = sum(1 for r in results if r["available"])
                logger.info(
                    "Health check: %d/%d agents healthy", healthy, len(results)
                )
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Health monitor loop error")


async def _workflow_pump_loop(interval: int = 3) -> None:
    """Single loop that advances ALL running workflows."""
    from src.database import async_session
    from src.services.workflow_execution import WorkflowExecutionService

    while True:
        try:
            await asyncio.sleep(interval)
            async with async_session() as db:
                engine = WorkflowExecutionService(db)
                await engine.pump_running_workflows()
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Workflow pump loop error")


async def _scheduler_loop(interval: int = 30) -> None:
    """Check for due schedules every 30 seconds."""
    from src.database import async_session
    from src.services.scheduler import SchedulerService

    while True:
        try:
            await asyncio.sleep(interval)
            async with async_session() as db:
                service = SchedulerService(db)
                await service.process_due_schedules()
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Scheduler loop error")


async def _webhook_log_cleanup_loop(retention_days: int = 90, interval: int = 86_400):
    """Delete webhook logs older than retention_days. Runs once per interval."""
    from src.database import async_session
    from src.models.webhook_log import WebhookLog

    while True:
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
            async with async_session() as session:
                result = await session.execute(
                    delete(WebhookLog).where(WebhookLog.created_at < cutoff)
                )
                await session.commit()
                if result.rowcount:
                    logger.info("Webhook log cleanup: deleted %d logs older than %d days", result.rowcount, retention_days)
        except Exception:
            logger.exception("Webhook log cleanup error")
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging(settings.log_level, settings.log_format)

    # Initialize Sentry if DSN is configured
    import os
    sentry_dsn = os.environ.get("SENTRY_DSN", "")
    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.scrubber import EventScrubber, DEFAULT_DENYLIST
            sentry_sdk.init(
                dsn=sentry_dsn,
                send_default_pii=False,
                event_scrubber=EventScrubber(denylist=DEFAULT_DENYLIST + [
                    "api_key", "llm_api_keys", "firebase_credentials_json",
                    "stripe_secret_key", "stripe_webhook_secret", "email",
                    "hashed_password", "authorization", "x-api-key",
                ]),
                traces_sample_rate=0.1 if not settings.debug else 1.0,
                environment="staging" if settings.debug else "production",
            )
            logger.info("Sentry initialized")
        except ImportError:
            logger.warning("SENTRY_DSN set but sentry-sdk not installed")

    from src.core.auth import _init_firebase
    _init_firebase()

    # Validate database connectivity (fail fast if unreachable)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception:
        logger.exception("Database connection failed")
        raise

    # Run Alembic migrations (non-blocking — skip on failure)
    if "sqlite" not in settings.database_url:
        try:
            import subprocess
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                logger.info("Alembic migrations applied successfully")
            else:
                logger.warning("Alembic migration failed: %s", result.stderr[-500:] if result.stderr else "no output")
        except subprocess.TimeoutExpired:
            logger.warning("Alembic migration timed out (30s) — skipping")
        except Exception:
            logger.warning("Alembic migration error — skipping", exc_info=True)
    else:
        # Auto-create tables for SQLite (dev/local only)
        from src.database import init_db
        await init_db()
        logger.info("SQLite tables auto-created")

    settings.warn_insecure_defaults()

    # Recover stale workflow runs from previous crash
    try:
        from src.database import async_session
        from src.services.workflow_execution import WorkflowExecutionService
        async with async_session() as db:
            wf_engine = WorkflowExecutionService(db)
            await wf_engine.recover_stale_runs()
    except Exception:
        logger.warning("Workflow recovery failed — skipping", exc_info=True)

    # Start background health monitor (every 5 minutes)
    health_task = asyncio.create_task(_health_monitor_loop(interval=300))

    # Start webhook log cleanup (daily, 90-day retention)
    cleanup_task = asyncio.create_task(_webhook_log_cleanup_loop(
        retention_days=90, interval=86_400,
    ))

    # Start workflow pump loop (every 3 seconds)
    workflow_pump_task = asyncio.create_task(_workflow_pump_loop(interval=3))

    # Start scheduler loop (every 30 seconds)
    scheduler_task = asyncio.create_task(_scheduler_loop(interval=30))

    logger.info("CrewHub startup complete")
    yield

    # Shutdown
    health_task.cancel()
    cleanup_task.cancel()
    workflow_pump_task.cancel()
    scheduler_task.cancel()
    for task in (health_task, cleanup_task, workflow_pump_task, scheduler_task):
        try:
            await task
        except asyncio.CancelledError:
            pass
    logger.info("CrewHub shutting down")


app = FastAPI(
    title=settings.app_name,
    description="CrewHub — discover, negotiate, and transact between AI agents",
    version="0.4.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    # Disable automatic 307 redirects for trailing slashes. Behind HF Spaces
    # reverse proxy the Location header uses http:// causing Mixed Content
    # errors on the HTTPS frontend. Accept both /path and /path/ as-is.
    redirect_slashes=False,
)


# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        if settings.force_https:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    """Inject X-RateLimit-* headers when rate limit info is available."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        info = getattr(request.state, "rate_limit_info", None)
        if info:
            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(info["reset"])
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitHeadersMiddleware)
app.add_middleware(RequestTracingMiddleware)

# HTTPS redirect (production only)
if settings.force_https:
    from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
    app.add_middleware(HTTPSRedirectMiddleware)

# Request body size limit (10 MB)
MAX_BODY_SIZE = 10 * 1024 * 1024


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_SIZE:
        return JSONResponse(status_code=413, content={"detail": "Request body too large"})
    return await call_next(request)


# CORS — allow the dashboard and existing site
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Primary domain
        "https://crewhubai.com",
        "https://www.crewhubai.com",
        "https://staging.crewhubai.com",
        "https://api.crewhubai.com",
        # Staging frontend
        "https://marketplace-staging.aidigitalcrew.com",
        # HuggingFace Spaces (direct access)
        "https://arimatch1-crewhub.hf.space",
        "https://arimatch1-crewhub-staging.hf.space",
        # Local development
        "http://localhost:3000",
        "http://localhost:5173",
        # Tauri desktop app
        "tauri://localhost",
        "https://tauri.localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(MarketplaceError)
async def marketplace_error_handler(request: Request, exc: MarketplaceError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(MissingAPIKeyError)
async def missing_api_key_handler(request: Request, exc: MissingAPIKeyError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": str(exc),
            "error_type": "missing_api_key",
            "provider": exc.provider,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions — log details, return sanitized 500."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    content = {"detail": "An internal error occurred. Please try again later."}
    if settings.debug:
        import traceback
        content["debug_error"] = f"{type(exc).__name__}: {exc}"
        content["debug_traceback"] = traceback.format_exc()
    return JSONResponse(status_code=500, content=content)


# Import and include routers
from src.api.agents import router as agents_router  # noqa: E402
from src.api.auth import router as auth_router  # noqa: E402
from src.api.credits import router as credits_router  # noqa: E402
from src.api.discovery import router as discovery_router  # noqa: E402
from src.api.health import router as health_router  # noqa: E402
from src.api.tasks import router as tasks_router  # noqa: E402
from src.api.llm_keys import router as llm_keys_router  # noqa: E402
from src.api.webhooks import router as webhooks_router  # noqa: E402
from src.api.imports import router as imports_router  # noqa: E402
from src.api.admin import router as admin_router  # noqa: E402
from src.api.a2a import router as a2a_router  # noqa: E402
from src.api.activity import router as activity_router  # noqa: E402
from src.api.llm_calls import router as llm_calls_router  # noqa: E402
from src.api.organizations import router as orgs_router  # noqa: E402
from src.api.anp import router as anp_router  # noqa: E402
from src.api.billing import router as billing_router  # noqa: E402
from src.api.suggestions import router as suggestions_router  # noqa: E402
from src.api.detect import router as detect_router  # noqa: E402
from src.api.validate import router as validate_router  # noqa: E402
from src.api.webhook_logs import router as webhook_logs_router  # noqa: E402
from src.mcp.router import router as mcp_resources_router  # noqa: E402
from src.api.telemetry import router as telemetry_router  # noqa: E402
from src.api.analytics import router as analytics_router  # noqa: E402
from src.api.crews import router as crews_router  # noqa: E402
from src.api.feedback import router as feedback_router  # noqa: E402
from src.api.guest_trial import router as guest_trial_router  # noqa: E402
from src.api.payouts import router as payouts_router  # noqa: E402
from src.api.supervisor import router as supervisor_router  # noqa: E402
from src.api.workflows import router as workflows_router  # noqa: E402
from src.api.schedules import router as schedules_router  # noqa: E402
from src.api.custom_agents import router as custom_agents_router  # noqa: E402
from src.api.channels import router as channels_router  # noqa: E402
from src.api.builder import router as builder_router  # noqa: E402

app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(agents_router, prefix=settings.api_v1_prefix)
app.include_router(discovery_router, prefix=settings.api_v1_prefix)
app.include_router(tasks_router, prefix=settings.api_v1_prefix)
app.include_router(credits_router, prefix=settings.api_v1_prefix)
app.include_router(llm_keys_router, prefix=settings.api_v1_prefix)
app.include_router(health_router)
app.include_router(webhooks_router, prefix=settings.api_v1_prefix)
app.include_router(imports_router, prefix=settings.api_v1_prefix)
app.include_router(admin_router, prefix=settings.api_v1_prefix)
app.include_router(a2a_router, prefix=settings.api_v1_prefix)
app.include_router(activity_router, prefix=settings.api_v1_prefix)
app.include_router(llm_calls_router, prefix=settings.api_v1_prefix)
app.include_router(orgs_router, prefix=settings.api_v1_prefix)
app.include_router(anp_router, prefix=settings.api_v1_prefix)
app.include_router(billing_router, prefix=settings.api_v1_prefix)
app.include_router(suggestions_router, prefix=settings.api_v1_prefix)
app.include_router(detect_router, prefix=settings.api_v1_prefix)
app.include_router(validate_router, prefix=settings.api_v1_prefix)
app.include_router(webhook_logs_router, prefix=settings.api_v1_prefix)
app.include_router(mcp_resources_router, prefix=settings.api_v1_prefix)
app.include_router(telemetry_router, prefix=settings.api_v1_prefix)
app.include_router(analytics_router, prefix=settings.api_v1_prefix)
app.include_router(crews_router, prefix=settings.api_v1_prefix)
app.include_router(feedback_router, prefix=settings.api_v1_prefix)
app.include_router(guest_trial_router, prefix=settings.api_v1_prefix)
app.include_router(payouts_router, prefix=settings.api_v1_prefix)
app.include_router(supervisor_router, prefix=settings.api_v1_prefix)
app.include_router(channels_router, prefix=settings.api_v1_prefix)
app.include_router(workflows_router, prefix=settings.api_v1_prefix)
app.include_router(schedules_router, prefix=settings.api_v1_prefix)
app.include_router(custom_agents_router, prefix=settings.api_v1_prefix)
app.include_router(builder_router, prefix=settings.api_v1_prefix)
# Also mount ANP well-known endpoint at root (no prefix)
app.include_router(anp_router)

# Mount MCP server — auto-generates MCP tools from all FastAPI endpoints
import importlib.util
import logging as _logging

_mcp_logger = _logging.getLogger(__name__)

if importlib.util.find_spec("fastapi_mcp") is not None:
    from fastapi_mcp import FastApiMCP
    mcp = FastApiMCP(
        app,
        name="CrewHub",
        description="AI Agent Marketplace — discover, delegate, and manage AI agents",
    )
    mcp.mount_http()  # Streamable HTTP transport at /mcp (recommended, replaces deprecated mount())
    _mcp_logger.info("MCP server mounted at /mcp (HTTP transport)")
else:
    _mcp_logger.warning("fastapi-mcp not installed — MCP server endpoint disabled")


# Root — HF Spaces readiness probe hits GET /
@app.get("/")
async def root():
    return {"name": "CrewHub", "status": "ok", "docs": "/docs" if settings.debug else None}


# Well-known agent card
@app.get("/.well-known/agent-card.json")
async def well_known_agent_card():
    return {
        "name": settings.app_name,
        "description": "CrewHub — Agent-to-Agent discovery and delegation marketplace",
        "url": "https://api.crewhubai.com",
        "version": "0.4.0",
        "capabilities": {
            "streaming": True,
            "pushNotifications": True,
        },
        "authentication": {
            "schemes": ["bearer", "apiKey"],
            "credentials": {
                "bearer": {"headerName": "Authorization", "prefix": "Bearer"},
                "apiKey": {"headerName": "X-API-Key"},
            },
        },
        "provider": {
            "organization": "CrewHub",
            "url": "https://crewhubai.com",
        },
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
        "skills": [
            {
                "id": "discover-agents",
                "name": "Discover Agents",
                "description": "Search and discover AI agents by capability, category, or intent",
            },
            {
                "id": "delegate-task",
                "name": "Delegate Task",
                "description": "Delegate a task to a discovered agent and track its completion",
            },
        ],
    }
