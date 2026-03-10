"""Comprehensive tests for the auto-delegation and suggestion feature.

Tests cover:
1. Schema validation (SuggestionRequest, SkillSuggestion, SuggestionResponse)
2. Semantic scoring logic (_score_skills_python)
3. Keyword fallback logic (_score_skills_keyword)
4. suggest_delegation() end-to-end with DB
5. check_skill_mismatch()
6. Mismatch warning in create_task (validate_match=true)
7. API route /tasks/suggest via TestClient
8. Edge cases (no agents, no skills, empty message, low confidence)
"""

import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

# Ensure we use SQLite for tests
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test_delegation.db")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from src.schemas.suggestion import (
    SuggestionRequest,
    SuggestionResponse,
)
from src.schemas.task import TaskCreate


# ============================================================
# 1. Schema Validation Tests
# ============================================================


class TestSuggestionSchemas:
    """Test request/response schema validation."""

    def test_suggestion_request_minimal(self):
        req = SuggestionRequest(message="Build a landing page")
        assert req.message == "Build a landing page"
        assert req.category is None
        assert req.tags == []
        assert req.max_credits is None
        assert req.limit == 3

    def test_suggestion_request_full(self):
        req = SuggestionRequest(
            message="Translate this document to French",
            category="engineering",
            tags=["translation", "nlp"],
            max_credits=50.0,
            limit=5,
        )
        assert req.category == "engineering"
        assert req.tags == ["translation", "nlp"]
        assert req.max_credits == 50.0
        assert req.limit == 5

    def test_suggestion_request_validates_message_length(self):
        with pytest.raises(ValidationError):
            SuggestionRequest(message="x" * 10_001)

    def test_suggestion_request_validates_limit_range(self):
        with pytest.raises(ValidationError):
            SuggestionRequest(message="test", limit=0)
        with pytest.raises(ValidationError):
            SuggestionRequest(message="test", limit=11)

    def test_suggestion_request_validates_max_credits(self):
        with pytest.raises(ValidationError):
            SuggestionRequest(message="test", max_credits=-1)

    def test_suggestion_response_empty(self):
        resp = SuggestionResponse(suggestions=[])
        assert resp.suggestions == []
        assert resp.fallback_used is False
        assert resp.hint is None

    def test_suggestion_response_with_hint(self):
        resp = SuggestionResponse(
            suggestions=[],
            fallback_used=True,
            hint="Configure an API key for better results.",
        )
        assert resp.fallback_used is True
        assert resp.hint is not None

    def test_task_create_has_validate_match(self):
        """Verify validate_match field was added to TaskCreate."""
        tc = TaskCreate(
            provider_agent_id=uuid.uuid4(),
            skill_id="test-skill",
            messages=[{"role": "user", "parts": [{"type": "text", "content": "hi"}]}],
            validate_match=True,
        )
        assert tc.validate_match is True

    def test_task_create_validate_match_defaults_false(self):
        tc = TaskCreate(
            provider_agent_id=uuid.uuid4(),
            skill_id="test-skill",
            messages=[{"role": "user", "parts": [{"type": "text", "content": "hi"}]}],
        )
        assert tc.validate_match is False


# ============================================================
# 2. Scoring Logic Tests (unit tests, no DB)
# ============================================================


class TestScoringLogic:
    """Test the static scoring methods on TaskBrokerService."""

    def _make_agent(self, name="Agent", category="engineering", skills=None):
        """Create a mock Agent with skills."""
        agent = MagicMock()
        agent.id = uuid.uuid4()
        agent.name = name
        agent.category = category
        agent.skills = skills or []
        agent.status = "active"
        return agent

    def _make_skill(self, name="Skill", description="A skill", embedding=None, avg_credits=0):
        """Create a mock AgentSkill."""
        skill = MagicMock()
        skill.id = uuid.uuid4()
        skill.name = name
        skill.description = description
        skill.embedding = embedding
        skill.avg_credits = avg_credits
        skill.skill_key = name.lower().replace(" ", "-")
        return skill

    def test_score_skills_python_basic(self):
        from src.services.task_broker import TaskBrokerService

        # Create a skill with a known embedding (unit vector along axis 0)
        embedding_a = [1.0, 0.0, 0.0]
        embedding_b = [0.0, 1.0, 0.0]

        skill_a = self._make_skill("Frontend Dev", "Build web pages", embedding=embedding_a)
        skill_b = self._make_skill("Translator", "Translate text", embedding=embedding_b)

        agent = self._make_agent(skills=[skill_a, skill_b])

        # Query embedding aligned with skill_a
        query = [0.9, 0.1, 0.0]
        scored = TaskBrokerService._score_skills_python([agent], query, max_credits=None)

        assert len(scored) == 2
        # skill_a should score higher (cosine sim closer to 1)
        scores_by_name = {s[1].name: s[2] for s in scored}
        assert scores_by_name["Frontend Dev"] > scores_by_name["Translator"]

    def test_score_skills_python_respects_max_credits(self):
        from src.services.task_broker import TaskBrokerService

        skill_cheap = self._make_skill("Cheap", "Cheap skill", embedding=[1.0, 0.0], avg_credits=5)
        skill_expensive = self._make_skill("Expensive", "Expensive skill", embedding=[1.0, 0.0], avg_credits=100)

        agent = self._make_agent(skills=[skill_cheap, skill_expensive])

        scored = TaskBrokerService._score_skills_python([agent], [1.0, 0.0], max_credits=10)
        assert len(scored) == 1
        assert scored[0][1].name == "Cheap"

    def test_score_skills_python_skips_no_embedding(self):
        from src.services.task_broker import TaskBrokerService

        skill_no_emb = self._make_skill("NoEmb", "No embedding", embedding=None)
        skill_emb = self._make_skill("WithEmb", "Has embedding", embedding=[1.0, 0.0])

        agent = self._make_agent(skills=[skill_no_emb, skill_emb])

        scored = TaskBrokerService._score_skills_python([agent], [1.0, 0.0], max_credits=None)
        assert len(scored) == 1
        assert scored[0][1].name == "WithEmb"

    def test_score_skills_keyword_basic(self):
        from src.services.task_broker import TaskBrokerService

        skill_a = self._make_skill("Frontend Developer", "Build responsive web pages and landing pages")
        skill_b = self._make_skill("Translator", "Translate documents between languages")

        agent = self._make_agent(skills=[skill_a, skill_b])

        message = "Build me a responsive landing page"
        scored = TaskBrokerService._score_skills_keyword([agent], message, max_credits=None)

        assert len(scored) >= 1
        # Frontend dev should match more keywords from "Build responsive landing page"
        if len(scored) > 1:
            scores_by_name = {s[1].name: s[2] for s in scored}
            assert scores_by_name.get("Frontend Developer", 0) >= scores_by_name.get("Translator", 0)

    def test_score_skills_keyword_no_match(self):
        from src.services.task_broker import TaskBrokerService

        skill = self._make_skill("Translator", "Translate documents")
        agent = self._make_agent(skills=[skill])

        scored = TaskBrokerService._score_skills_keyword([agent], "asdfghjkl", max_credits=None)
        assert len(scored) == 0

    def test_score_skills_keyword_respects_max_credits(self):
        from src.services.task_broker import TaskBrokerService

        skill = self._make_skill("Dev", "Build web pages", avg_credits=100)
        agent = self._make_agent(skills=[skill])

        scored = TaskBrokerService._score_skills_keyword([agent], "Build web pages", max_credits=10)
        assert len(scored) == 0

    def test_build_reason_labels(self):
        from src.services.task_broker import TaskBrokerService

        assert "Strong" in TaskBrokerService._build_reason(0.8, False)
        assert "Moderate" in TaskBrokerService._build_reason(0.5, False)
        assert "Weak" in TaskBrokerService._build_reason(0.1, False)
        assert "keyword" in TaskBrokerService._build_reason(0.8, True)
        assert "semantic" in TaskBrokerService._build_reason(0.8, False)


# ============================================================
# 3. Database Integration Tests (SQLite)
# ============================================================


@pytest.fixture
async def db_session():
    """Create an in-memory SQLite database with tables and return a session."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from src.database import Base

    # Import all models so Base.metadata includes them
    import src.models.user  # noqa: F401
    import src.models.agent  # noqa: F401
    import src.models.skill  # noqa: F401
    import src.models.task  # noqa: F401
    import src.models.transaction  # noqa: F401

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    await engine.dispose()


def _pad_embedding(values: list[float], dim: int = 1536) -> list[float]:
    """Pad a short embedding vector to the required dimension for pgvector."""
    return values + [0.0] * (dim - len(values))


@pytest.fixture
async def seed_data(db_session):
    """Seed the DB with a user, two agents, and skills with mock embeddings."""
    from src.models.user import User
    from src.models.agent import Agent, AgentStatus
    from src.models.skill import AgentSkill
    from src.config import settings

    dim = settings.embedding_dimension

    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        name="Test User",
    )
    db_session.add(user)

    # Agent 1: Frontend team
    agent1 = Agent(
        id=uuid.uuid4(),
        owner_id=user.id,
        name="Frontend Engineering",
        description="Builds web frontends",
        endpoint="https://example.com/agent1",
        status=AgentStatus.ACTIVE,
        category="engineering",
        tags=["frontend", "web"],
        pricing={"license_type": "open", "tiers": [], "model": "per_task", "credits": 0},
        security_schemes=[],
    )
    db_session.add(agent1)

    skill_fe = AgentSkill(
        id=uuid.uuid4(),
        agent_id=agent1.id,
        skill_key="frontend-developer",
        name="Frontend Developer",
        description="Build responsive web pages and landing pages",
        input_modes=["text"],
        output_modes=["text"],
        avg_credits=5,
        avg_latency_ms=3000,
        # Embedding: strong in "frontend" direction
        embedding=_pad_embedding([0.9, 0.3, 0.1, 0.0, 0.0], dim),
    )
    db_session.add(skill_fe)

    # Agent 2: Translation
    agent2 = Agent(
        id=uuid.uuid4(),
        owner_id=user.id,
        name="Translation Service",
        description="Translates documents between languages",
        endpoint="https://example.com/agent2",
        status=AgentStatus.ACTIVE,
        category="engineering",
        tags=["translation", "nlp"],
        pricing={"license_type": "open", "tiers": [], "model": "per_task", "credits": 0},
        security_schemes=[],
    )
    db_session.add(agent2)

    skill_tr = AgentSkill(
        id=uuid.uuid4(),
        agent_id=agent2.id,
        skill_key="translator",
        name="Translator",
        description="Translate text between languages",
        input_modes=["text"],
        output_modes=["text"],
        avg_credits=3,
        avg_latency_ms=2000,
        # Embedding: strong in "translation" direction
        embedding=_pad_embedding([0.1, 0.9, 0.2, 0.0, 0.0], dim),
    )
    db_session.add(skill_tr)

    await db_session.commit()

    return {
        "user": user,
        "agent1": agent1,
        "agent2": agent2,
        "skill_fe": skill_fe,
        "skill_tr": skill_tr,
    }


class TestSuggestDelegationIntegration:
    """Test suggest_delegation() against a real SQLite DB."""

    async def test_suggest_with_semantic_match(self, db_session, seed_data):
        """Semantic search should rank the matching skill higher."""
        from src.services.task_broker import TaskBrokerService

        service = TaskBrokerService(db_session)

        # Mock EmbeddingService to return a vector similar to frontend embedding
        with patch("src.core.embeddings.EmbeddingService") as MockEmb:
            instance = AsyncMock()
            instance.generate = AsyncMock(return_value=_pad_embedding([0.85, 0.2, 0.1, 0.0, 0.0]))
            MockEmb.return_value = instance

            result = await service.suggest_delegation(
                message="Build a responsive landing page with hero section",
                limit=3,
            )

        assert len(result.suggestions) == 2
        assert result.fallback_used is False
        # Frontend skill should rank first (higher cosine similarity)
        assert result.suggestions[0].skill.skill_key == "frontend-developer"
        assert result.suggestions[0].confidence > result.suggestions[1].confidence

    async def test_suggest_with_translation_query(self, db_session, seed_data):
        """Translation query should rank translator skill first."""
        from src.services.task_broker import TaskBrokerService

        service = TaskBrokerService(db_session)

        with patch("src.core.embeddings.EmbeddingService") as MockEmb:
            instance = AsyncMock()
            # Vector similar to translation embedding
            instance.generate = AsyncMock(return_value=_pad_embedding([0.1, 0.85, 0.15, 0.0, 0.0]))
            MockEmb.return_value = instance

            result = await service.suggest_delegation(
                message="Translate this document to French",
                limit=3,
            )

        assert len(result.suggestions) == 2
        assert result.suggestions[0].skill.skill_key == "translator"

    async def test_suggest_falls_back_to_keyword(self, db_session, seed_data):
        """When embedding fails, should fall back to keyword search."""
        from src.core.embeddings import MissingAPIKeyError
        from src.services.task_broker import TaskBrokerService

        service = TaskBrokerService(db_session)

        with patch("src.core.embeddings.EmbeddingService") as MockEmb:
            instance = AsyncMock()
            instance.generate = AsyncMock(side_effect=MissingAPIKeyError("openai"))
            MockEmb.return_value = instance

            result = await service.suggest_delegation(
                message="Build web pages and landing pages",
                limit=3,
            )

        assert result.fallback_used is True
        assert result.hint is not None
        assert "API key" in result.hint
        # Should still find frontend skill via keyword match
        assert len(result.suggestions) > 0

    async def test_suggest_no_agents(self, db_session):
        """Empty DB should return empty suggestions."""
        from src.services.task_broker import TaskBrokerService

        service = TaskBrokerService(db_session)

        with patch("src.core.embeddings.EmbeddingService") as MockEmb:
            instance = AsyncMock()
            instance.generate = AsyncMock(return_value=_pad_embedding([1.0, 0.0]))
            MockEmb.return_value = instance

            result = await service.suggest_delegation(message="anything")

        assert len(result.suggestions) == 0
        assert "No active agents" in (result.hint or "")

    async def test_suggest_respects_max_credits(self, db_session, seed_data):
        """max_credits filter should exclude expensive skills."""
        from src.services.task_broker import TaskBrokerService

        service = TaskBrokerService(db_session)

        with patch("src.core.embeddings.EmbeddingService") as MockEmb:
            instance = AsyncMock()
            instance.generate = AsyncMock(return_value=_pad_embedding([0.85, 0.2, 0.1, 0.0, 0.0]))
            MockEmb.return_value = instance

            # Frontend skill costs 5 credits, translator costs 3
            result = await service.suggest_delegation(
                message="Build a landing page",
                max_credits=4,
                limit=3,
            )

        # Should only include translator (3 credits) since frontend is 5
        skill_keys = [s.skill.skill_key for s in result.suggestions]
        assert "frontend-developer" not in skill_keys
        assert "translator" in skill_keys

    async def test_suggest_respects_category_filter(self, db_session, seed_data):
        """Category filter should narrow results."""
        from src.services.task_broker import TaskBrokerService

        service = TaskBrokerService(db_session)

        with patch("src.core.embeddings.EmbeddingService") as MockEmb:
            instance = AsyncMock()
            instance.generate = AsyncMock(return_value=_pad_embedding([0.5, 0.5, 0.0, 0.0, 0.0]))
            MockEmb.return_value = instance

            # Both agents are in "engineering" — this should return both
            result = await service.suggest_delegation(
                message="anything",
                category="engineering",
                limit=5,
            )
            assert len(result.suggestions) == 2

            # Non-existent category — should return none
            result = await service.suggest_delegation(
                message="anything",
                category="nonexistent",
                limit=5,
            )
            assert len(result.suggestions) == 0

    async def test_suggest_low_confidence_flag(self, db_session, seed_data):
        """Orthogonal embedding should produce low confidence."""
        from src.services.task_broker import TaskBrokerService

        service = TaskBrokerService(db_session)

        with patch("src.core.embeddings.EmbeddingService") as MockEmb:
            instance = AsyncMock()
            # Orthogonal to both skill embeddings
            instance.generate = AsyncMock(return_value=_pad_embedding([0.0, 0.0, 0.0, 0.0, 1.0]))
            MockEmb.return_value = instance

            result = await service.suggest_delegation(
                message="asdfghjkl random gibberish",
                limit=3,
            )

        # Both suggestions should be low confidence
        for s in result.suggestions:
            assert s.low_confidence is True
            assert s.confidence < 0.3

    async def test_suggest_respects_limit(self, db_session, seed_data):
        """Limit parameter should cap the number of suggestions."""
        from src.services.task_broker import TaskBrokerService

        service = TaskBrokerService(db_session)

        with patch("src.core.embeddings.EmbeddingService") as MockEmb:
            instance = AsyncMock()
            instance.generate = AsyncMock(return_value=_pad_embedding([0.5, 0.5, 0.0, 0.0, 0.0]))
            MockEmb.return_value = instance

            result = await service.suggest_delegation(message="anything", limit=1)

        assert len(result.suggestions) == 1


class TestCheckSkillMismatch:
    """Test the mismatch check on manual task creation."""

    async def test_mismatch_detected(self, db_session, seed_data):
        """Orthogonal message + frontend skill should warn."""
        from src.services.task_broker import TaskBrokerService

        service = TaskBrokerService(db_session)

        with patch("src.core.embeddings.EmbeddingService") as MockEmb:
            instance = AsyncMock()
            # Embedding orthogonal to frontend skill [0.9, 0.3, 0.1, 0.0, 0.0]
            instance.generate = AsyncMock(return_value=_pad_embedding([0.0, 0.0, 0.0, 1.0, 0.0]))
            MockEmb.return_value = instance

            warning = await service.check_skill_mismatch(
                messages=[{"role": "user", "parts": [{"type": "text", "content": "Translate to French"}]}],
                skill_id=seed_data["skill_fe"].skill_key,
                agent_id=seed_data["agent1"].id,
            )

        assert warning is not None
        assert "may not match" in warning
        assert "Frontend Developer" in warning

    async def test_good_match_no_warning(self, db_session, seed_data):
        """Frontend message + frontend skill should not warn."""
        from src.services.task_broker import TaskBrokerService

        service = TaskBrokerService(db_session)

        with patch("src.core.embeddings.EmbeddingService") as MockEmb:
            instance = AsyncMock()
            # Frontend-like embedding (matches frontend skill)
            instance.generate = AsyncMock(return_value=_pad_embedding([0.9, 0.3, 0.1, 0.0, 0.0]))
            MockEmb.return_value = instance

            warning = await service.check_skill_mismatch(
                messages=[{"role": "user", "parts": [{"type": "text", "content": "Build a web page"}]}],
                skill_id=seed_data["skill_fe"].skill_key,
                agent_id=seed_data["agent1"].id,
            )

        assert warning is None

    async def test_mismatch_graceful_on_no_embedding_key(self, db_session, seed_data):
        """If no embedding API key, mismatch check should return None (not crash)."""
        from src.core.embeddings import MissingAPIKeyError
        from src.services.task_broker import TaskBrokerService

        service = TaskBrokerService(db_session)

        with patch("src.core.embeddings.EmbeddingService") as MockEmb:
            instance = AsyncMock()
            instance.generate = AsyncMock(side_effect=MissingAPIKeyError("openai"))
            MockEmb.return_value = instance

            warning = await service.check_skill_mismatch(
                messages=[{"role": "user", "parts": [{"type": "text", "content": "anything"}]}],
                skill_id=seed_data["skill_fe"].skill_key,
                agent_id=seed_data["agent1"].id,
            )

        assert warning is None

    async def test_mismatch_no_skill_embedding(self, db_session, seed_data):
        """If skill has no embedding, should return None."""
        from src.services.task_broker import TaskBrokerService
        from src.models.skill import AgentSkill

        # Add a skill without embedding
        skill_no_emb = AgentSkill(
            id=uuid.uuid4(),
            agent_id=seed_data["agent1"].id,
            skill_key="no-embedding-skill",
            name="No Embedding",
            description="A skill without embedding",
            input_modes=["text"],
            output_modes=["text"],
            avg_credits=0,
            avg_latency_ms=0,
            embedding=None,
        )
        db_session.add(skill_no_emb)
        await db_session.commit()

        service = TaskBrokerService(db_session)
        warning = await service.check_skill_mismatch(
            messages=[{"role": "user", "parts": [{"type": "text", "content": "anything"}]}],
            skill_id="no-embedding-skill",
            agent_id=seed_data["agent1"].id,
        )
        assert warning is None

    async def test_mismatch_empty_messages(self, db_session, seed_data):
        """Empty messages should return None."""
        from src.services.task_broker import TaskBrokerService

        service = TaskBrokerService(db_session)
        warning = await service.check_skill_mismatch(
            messages=[{"role": "user", "parts": []}],
            skill_id=seed_data["skill_fe"].skill_key,
            agent_id=seed_data["agent1"].id,
        )
        assert warning is None


# ============================================================
# 4. API Route Tests (FastAPI TestClient)
# ============================================================


class TestSuggestionAPIRoute:
    """Test the POST /tasks/suggest endpoint."""

    async def test_suggest_endpoint_returns_suggestions(self):
        """Endpoint should return SuggestionResponse."""
        from src.core.auth import get_current_user
        from src.services.task_broker import TaskBrokerService
        from httpx import AsyncClient, ASGITransport
        from src.main import app

        fake_user = {"id": str(uuid.uuid4()), "firebase_uid": None}
        app.dependency_overrides[get_current_user] = lambda: fake_user

        mock_response = SuggestionResponse(
            suggestions=[],
            fallback_used=False,
            hint=None,
        )

        with patch("src.api.suggestions._resolve_user_keys", new_callable=AsyncMock) as mock_keys:
            mock_keys.return_value = ({}, str(uuid.uuid4()), "free")
            with patch.object(TaskBrokerService, "suggest_delegation", new_callable=AsyncMock) as mock_suggest:
                mock_suggest.return_value = mock_response

                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(
                        "/api/v1/tasks/suggest",
                        json={"message": "Build a landing page"},
                    )

        app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert "suggestions" in data
        assert "fallback_used" in data

    async def test_suggest_endpoint_validates_input(self):
        """Endpoint should reject invalid input (missing 'message')."""
        from src.core.auth import get_current_user
        from httpx import AsyncClient, ASGITransport
        from src.main import app

        fake_user = {"id": str(uuid.uuid4()), "firebase_uid": None}
        app.dependency_overrides[get_current_user] = lambda: fake_user

        with patch("src.api.suggestions._resolve_user_keys", new_callable=AsyncMock) as mock_keys:
            mock_keys.return_value = ({}, str(uuid.uuid4()), "free")

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/tasks/suggest", json={})

        app.dependency_overrides.clear()
        assert resp.status_code == 422

    async def test_suggest_endpoint_rejects_invalid_limit(self):
        """Endpoint should reject limit=0."""
        from src.core.auth import get_current_user
        from httpx import AsyncClient, ASGITransport
        from src.main import app

        fake_user = {"id": str(uuid.uuid4()), "firebase_uid": None}
        app.dependency_overrides[get_current_user] = lambda: fake_user

        with patch("src.api.suggestions._resolve_user_keys", new_callable=AsyncMock) as mock_keys:
            mock_keys.return_value = ({}, str(uuid.uuid4()), "free")

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/tasks/suggest",
                    json={"message": "test", "limit": 0},
                )

        app.dependency_overrides.clear()
        assert resp.status_code == 422


# ============================================================
# 5. Cosine Similarity Edge Cases
# ============================================================


class TestCosineSimilarity:
    """Test the cosine similarity function edge cases."""

    def test_identical_vectors(self):
        from src.services.discovery import DiscoveryService

        v = [1.0, 2.0, 3.0]
        sim = DiscoveryService._cosine_similarity(v, v)
        assert abs(sim - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        from src.services.discovery import DiscoveryService

        a = [1.0, 0.0]
        b = [0.0, 1.0]
        sim = DiscoveryService._cosine_similarity(a, b)
        assert abs(sim) < 1e-6

    def test_opposite_vectors(self):
        from src.services.discovery import DiscoveryService

        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        sim = DiscoveryService._cosine_similarity(a, b)
        assert abs(sim - (-1.0)) < 1e-6

    def test_empty_vectors(self):
        from src.services.discovery import DiscoveryService

        assert DiscoveryService._cosine_similarity([], []) == 0.0

    def test_mismatched_lengths(self):
        from src.services.discovery import DiscoveryService

        assert DiscoveryService._cosine_similarity([1.0], [1.0, 2.0]) == 0.0

    def test_zero_vector(self):
        from src.services.discovery import DiscoveryService

        assert DiscoveryService._cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0
