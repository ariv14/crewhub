from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import settings
from src.core.exceptions import MarketplaceError
from src.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize Firebase and database
    from src.core.auth import _init_firebase
    _init_firebase()
    await init_db()
    yield
    # Shutdown


app = FastAPI(
    title=settings.app_name,
    description="CrewHub — discover, negotiate, and transact between AI agents",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)


# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


app.add_middleware(SecurityHeadersMiddleware)

# CORS — allow the dashboard and existing site
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://aidigitalcrew.com",
        "https://www.aidigitalcrew.com",
        "https://marketplace.aidigitalcrew.com",
        "http://localhost:3000",  # Local Next.js dev
        "http://localhost:5173",  # Local Vite dev
        "tauri://localhost",      # Tauri desktop app
        "https://tauri.localhost", # Tauri desktop app (HTTPS)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(MarketplaceError)
async def marketplace_error_handler(request: Request, exc: MarketplaceError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


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
from src.api.anp import router as anp_router  # noqa: E402
from src.mcp.router import router as mcp_resources_router  # noqa: E402

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
app.include_router(anp_router, prefix=settings.api_v1_prefix)
app.include_router(mcp_resources_router, prefix=settings.api_v1_prefix)
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
    mcp.mount()  # Exposes /mcp endpoint
    _mcp_logger.info("MCP server mounted at /mcp")
else:
    _mcp_logger.warning("fastapi-mcp not installed — MCP server endpoint disabled")


# Well-known agent card
@app.get("/.well-known/agent-card.json")
async def well_known_agent_card():
    return {
        "name": settings.app_name,
        "description": "CrewHub — Agent-to-Agent discovery and delegation marketplace",
        "url": "https://api.aidigitalcrew.com",
        "version": "0.1.0",
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
            "organization": "AI Digital Crew",
            "url": "https://aidigitalcrew.com",
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
