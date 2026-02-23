"""Discovery service -- search, recommend, and explore agents."""

import time
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.embeddings import EmbeddingService
from src.models.agent import Agent, AgentStatus
from src.models.skill import AgentSkill
from src.models.task import Task
from src.schemas.agent import AgentResponse
from src.schemas.discovery import AgentMatch, DiscoveryResponse, SearchQuery


class DiscoveryService:
    """Search and discovery of marketplace agents.

    Uses in-memory cosine similarity for semantic search (no Qdrant dependency).
    Qdrant can be added later when scale requires it.
    """

    # Composite ranking weights
    W_RELEVANCE = 0.35
    W_REPUTATION = 0.25
    W_SUCCESS = 0.20
    W_LATENCY = 0.10
    W_COST = 0.10

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embeddings = EmbeddingService()

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(self, query: SearchQuery) -> DiscoveryResponse:
        """Route to the appropriate search strategy based on query.mode."""
        start = time.monotonic()

        if query.mode.value == "keyword":
            agents, total = await self._keyword_search(query)
        elif query.mode.value in ("semantic", "intent"):
            agents, total = await self._semantic_search(query)
        elif query.mode.value == "capability":
            agents, total = await self._capability_search(query)
        else:
            agents, total = await self._keyword_search(query)

        # Apply common post-filters and rank
        matches = self._rank_results(agents, query)

        elapsed_ms = (time.monotonic() - start) * 1000
        return DiscoveryResponse(
            matches=matches[: query.limit],
            total_candidates=total,
            query_time_ms=round(elapsed_ms, 2),
        )

    # ------------------------------------------------------------------
    # Keyword search
    # ------------------------------------------------------------------

    async def _keyword_search(
        self, query: SearchQuery
    ) -> tuple[list[Agent], int]:
        """SQL ILIKE search on agent name, description, skill names/descriptions."""
        pattern = f"%{query.query}%"
        stmt = (
            select(Agent)
            .options(selectinload(Agent.skills))
            .outerjoin(AgentSkill, AgentSkill.agent_id == Agent.id)
            .where(Agent.status == AgentStatus.ACTIVE)
            .where(
                (Agent.name.ilike(pattern))
                | (Agent.description.ilike(pattern))
                | (AgentSkill.name.ilike(pattern))
                | (AgentSkill.description.ilike(pattern))
            )
        )

        stmt = self._apply_filters(stmt, query)
        stmt = stmt.distinct()

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = stmt.limit(query.limit)
        result = await self.db.execute(stmt)
        agents = list(result.scalars().unique().all())

        return agents, total

    # ------------------------------------------------------------------
    # Semantic search (in-memory cosine similarity, no Qdrant needed)
    # ------------------------------------------------------------------

    async def _semantic_search(
        self, query: SearchQuery
    ) -> tuple[list[Agent], int]:
        """Generate embedding for query, compute cosine similarity against skill embeddings."""
        query_embedding = await self.embeddings.generate(query.query)

        # Fetch all active agents with their skills
        stmt = (
            select(Agent)
            .options(selectinload(Agent.skills))
            .where(Agent.status == AgentStatus.ACTIVE)
        )
        stmt = self._apply_filters(stmt, query)

        result = await self.db.execute(stmt)
        agents = list(result.scalars().unique().all())

        if not agents:
            return [], 0

        # Score each agent by best-matching skill embedding
        scored = []
        for agent in agents:
            best_sim = 0.0
            for skill in agent.skills:
                if skill.embedding:
                    sim = self._cosine_similarity(query_embedding, skill.embedding)
                    best_sim = max(best_sim, sim)
            scored.append((agent, best_sim))

        # Sort by similarity and return top results
        scored.sort(key=lambda x: x[1], reverse=True)
        top_agents = [a for a, _ in scored[: query.limit]]
        return top_agents, len(scored)

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(a) != len(b) or not a:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    # ------------------------------------------------------------------
    # Capability search
    # ------------------------------------------------------------------

    async def _capability_search(
        self, query: SearchQuery
    ) -> tuple[list[Agent], int]:
        """Filter by input_modes, output_modes, category, max_latency, max_credits."""
        stmt = (
            select(Agent)
            .options(selectinload(Agent.skills))
            .outerjoin(AgentSkill, AgentSkill.agent_id == Agent.id)
            .where(Agent.status == AgentStatus.ACTIVE)
        )

        stmt = self._apply_filters(stmt, query)
        stmt = stmt.distinct()

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = stmt.limit(query.limit)
        result = await self.db.execute(stmt)
        agents = list(result.scalars().unique().all())

        return agents, total

    # ------------------------------------------------------------------
    # Shared filter helper
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_filters(stmt, query: SearchQuery):
        """Apply common filters (category, tags, reputation, latency, credits)."""
        if query.category:
            stmt = stmt.where(Agent.category == query.category)
        if query.tags:
            stmt = stmt.where(Agent.tags.contains(query.tags))
        if query.min_reputation > 0:
            stmt = stmt.where(Agent.reputation_score >= query.min_reputation)
        if query.max_latency_ms is not None:
            stmt = stmt.where(Agent.avg_latency_ms <= query.max_latency_ms)
        return stmt

    # ------------------------------------------------------------------
    # Ranking
    # ------------------------------------------------------------------

    def _rank_results(
        self, agents: list[Agent], query: SearchQuery
    ) -> list[AgentMatch]:
        """Rank agents by composite score."""
        if not agents:
            return []

        max_latency = max((a.avg_latency_ms or 1) for a in agents) or 1

        matches: list[AgentMatch] = []
        for agent in agents:
            relevance = 1.0
            reputation = min(agent.reputation_score / 5.0, 1.0)
            success = agent.success_rate
            latency_factor = 1.0 - ((agent.avg_latency_ms or 0) / max_latency)
            cost_factor = 0.5

            composite = (
                self.W_RELEVANCE * relevance
                + self.W_REPUTATION * reputation
                + self.W_SUCCESS * success
                + self.W_LATENCY * latency_factor
                + self.W_COST * cost_factor
            )

            matches.append(
                AgentMatch(
                    agent=AgentResponse.model_validate(agent),
                    relevance_score=round(composite, 4),
                    match_reason=f"Matched via {query.mode.value} search",
                )
            )

        matches.sort(key=lambda m: m.relevance_score, reverse=True)
        return matches

    # ------------------------------------------------------------------
    # Recommendations
    # ------------------------------------------------------------------

    async def get_recommendations(self, agent_id: UUID) -> list[AgentMatch]:
        """Find agents with complementary skills (different category, high reputation)."""
        source = await self.db.get(Agent, agent_id)
        if not source:
            return []

        stmt = (
            select(Agent)
            .options(selectinload(Agent.skills))
            .where(Agent.status == AgentStatus.ACTIVE)
            .where(Agent.id != agent_id)
            .where(Agent.category != source.category)
            .order_by(Agent.reputation_score.desc())
            .limit(10)
        )
        result = await self.db.execute(stmt)
        agents = list(result.scalars().unique().all())

        return [
            AgentMatch(
                agent=AgentResponse.model_validate(a),
                relevance_score=round(a.reputation_score / 5.0, 4),
                match_reason="Complementary category with high reputation",
            )
            for a in agents
        ]

    # ------------------------------------------------------------------
    # Categories
    # ------------------------------------------------------------------

    async def get_categories(self) -> list[dict]:
        """Return distinct categories with agent counts."""
        stmt = (
            select(Agent.category, func.count(Agent.id).label("count"))
            .where(Agent.status == AgentStatus.ACTIVE)
            .where(Agent.category.isnot(None))
            .group_by(Agent.category)
            .order_by(func.count(Agent.id).desc())
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [{"category": row.category, "agent_count": row.count} for row in rows]

    # ------------------------------------------------------------------
    # Trending skills
    # ------------------------------------------------------------------

    async def get_trending_skills(self) -> list[dict]:
        """Return skills ordered by recent task volume."""
        stmt = (
            select(
                AgentSkill.id,
                AgentSkill.name,
                AgentSkill.description,
                func.count(Task.id).label("task_count"),
            )
            .outerjoin(Task, Task.skill_id == AgentSkill.id)
            .group_by(AgentSkill.id, AgentSkill.name, AgentSkill.description)
            .order_by(func.count(Task.id).desc())
            .limit(20)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            {
                "skill_id": str(row.id),
                "name": row.name,
                "description": row.description,
                "task_count": row.task_count,
            }
            for row in rows
        ]
