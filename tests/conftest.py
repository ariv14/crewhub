"""Shared test fixtures for the CrewHub test suite.

Uses aiosqlite for an in-memory SQLite database so that tests run
without any external services (PostgreSQL, Redis, Qdrant, etc.).
"""

import asyncio
import os
import sys
import uuid

# FastApiMCP schema resolution hits infinite recursion on self-referencing
# Pydantic schemas (SupervisorPlanStep.sub_steps). Prevent the import
# during tests by removing the spec finder result.
sys.modules.setdefault("fastapi_mcp", None)  # type: ignore[arg-type]
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.config import settings
from src.database import Base, get_db
from src.main import app

# Enable debug mode for tests (allows credit purchase endpoint, etc.)
settings.debug = True

# ---------------------------------------------------------------------------
# In-memory SQLite engine (aiosqlite)
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture()
async def engine():
    """Create an async SQLite engine for each test.

    A fresh engine per test guarantees full isolation.
    """
    _engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        # StaticPool ensures all connections share the same in-memory database.
        # Without this, code that opens its own session (e.g. _api_key_lookup)
        # would get a fresh empty DB and fail with "no such table".
        poolclass=StaticPool,
        pool_pre_ping=False,
    )

    # SQLite needs foreign-key enforcement turned on explicitly.
    @event.listens_for(_engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    yield _engine
    await _engine.dispose()


@pytest_asyncio.fixture()
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide an AsyncSession that creates all tables before the test and
    drops them afterwards, ensuring a clean slate for every test function.
    """
    # Import all models so that Base.metadata is fully populated.
    import src.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    _async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Record existing tasks so we only clean up tasks spawned during this test.
    pre_test_tasks = asyncio.all_tasks()

    async with _async_session() as session:
        yield session

    # Cancel tasks spawned during the test (e.g. A2A dispatch background tasks)
    # before dropping tables, otherwise SQLite's single-writer lock errors out.
    for task in asyncio.all_tasks() - pre_test_tasks:
        if not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def client(engine, db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """httpx AsyncClient wired to the FastAPI application with the database
    dependency overridden to use the test session.
    """
    import src.database as _db_module

    async def _override_get_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db] = _override_get_db

    # Also patch the module-level async_session used by _api_key_lookup
    _original_session = _db_module.async_session
    _db_module.async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    _db_module.async_session = _original_session
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _unique_email() -> str:
    """Generate a unique email for test user registration."""
    return f"test-{uuid.uuid4().hex[:8]}@example.com"


@pytest_asyncio.fixture()
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register a fresh test user and return Authorization headers with a
    valid JWT bearer token.
    """
    email = _unique_email()
    password = "TestPassword123"

    # Register
    register_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": "Test User"},
    )
    assert register_resp.status_code == 201, (
        f"Registration failed: {register_resp.status_code} {register_resp.text}"
    )

    # Login to obtain a token
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password, "name": "Test User"},
    )
    assert login_resp.status_code == 200, (
        f"Login failed: {login_resp.status_code} {login_resp.text}"
    )

    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_agent_payload(
    name: str = "Test Agent",
    description: str = "A test agent for automated testing",
    category: str = "general",
    **overrides,
) -> dict:
    """Build a valid AgentCreate payload for test registrations."""
    payload = {
        "name": name,
        "description": description,
        "version": "1.0.0",
        "endpoint": f"https://test-agent-{uuid.uuid4().hex[:8]}.example.com/a2a",
        "capabilities": {"streaming": False},
        "skills": [
            {
                "skill_key": "summarize",
                "name": "Summarize Text",
                "description": "Summarize a given document or text block",
                "input_modes": ["text"],
                "output_modes": ["text"],
                "examples": [],
                "avg_credits": 5.0,
                "avg_latency_ms": 2000,
            }
        ],
        "security_schemes": [],
        "category": category,
        "tags": ["test"],
        "pricing": {"model": "per_task", "credits": 5.0},
    }
    payload.update(overrides)
    return payload


@pytest_asyncio.fixture()
async def registered_agent(
    client: AsyncClient, auth_headers: dict[str, str]
) -> dict:
    """Register a test agent via the API and return the full agent response dict."""
    payload = _make_agent_payload()
    resp = await client.post(
        "/api/v1/agents/",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 201, (
        f"Agent registration failed: {resp.status_code} {resp.text}"
    )
    return resp.json()


@pytest_asyncio.fixture()
async def admin_headers(client: AsyncClient, db_session: AsyncSession) -> dict[str, str]:
    """Register a test user, promote to admin via DB, and return auth headers."""
    email = _unique_email()
    password = "AdminPass123"

    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": "Admin User"},
    )
    assert reg.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password, "name": "Admin User"},
    )
    assert login.status_code == 200

    # Promote to admin via direct DB update
    from sqlalchemy import update
    from src.models.user import User

    stmt = update(User).where(User.email == email).values(is_admin=True)
    await db_session.execute(stmt)
    await db_session.commit()

    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture()
async def second_auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register a second distinct test user and return auth headers."""
    email = _unique_email()
    password = "SecondPass123"

    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": "Second User"},
    )
    assert reg.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password, "name": "Second User"},
    )
    assert login.status_code == 200

    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Stripe / billing helpers
# ---------------------------------------------------------------------------

stripe_configured = pytest.mark.skipif(
    not os.environ.get("STRIPE_SECRET_KEY"),
    reason="STRIPE_SECRET_KEY not set",
)


@pytest_asyncio.fixture()
async def premium_user_headers(
    client: AsyncClient, db_session: AsyncSession
) -> dict[str, str]:
    """Register a user and set account_tier='premium' via DB."""
    from src.models.user import User

    email = _unique_email()
    password = "PremiumPass123"

    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": "Premium User"},
    )
    assert reg.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password, "name": "Premium User"},
    )
    assert login.status_code == 200

    stmt = update(User).where(User.email == email).values(account_tier="premium")
    await db_session.execute(stmt)
    await db_session.commit()

    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture()
async def user_with_llm_key(
    client: AsyncClient, auth_headers: dict[str, str]
) -> dict[str, str]:
    """Auth headers for a user with a pre-configured OpenAI LLM key."""
    resp = await client.put(
        "/api/v1/llm-keys/openai",
        json={"provider": "openai", "api_key": "sk-test-key-for-fixture"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    return auth_headers


# ---------------------------------------------------------------------------
# Embedding rate-limit isolation
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_embedding_rate_limits():
    """Clear the in-memory free-tier rate limiter between tests."""
    from src.core.embeddings import _free_tier_usage

    _free_tier_usage.clear()
    yield
    _free_tier_usage.clear()
