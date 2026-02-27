"""Shared test fixtures for the CrewHub test suite.

Uses aiosqlite for an in-memory SQLite database so that tests run
without any external services (PostgreSQL, Redis, Qdrant, etc.).
"""

import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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
        # SQLite does not support pool_size / max_overflow; use StaticPool
        # so that the same in-memory database is reused across connections.
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

    async with _async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """httpx AsyncClient wired to the FastAPI application with the database
    dependency overridden to use the test session.
    """

    async def _override_get_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

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
    password = "testpassword123"

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
        "endpoint": "https://test-agent.example.com/a2a",
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
