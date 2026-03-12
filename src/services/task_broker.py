"""Task broker service -- create, manage, and rate tasks between agents."""

import asyncio
import logging
import sys
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config import settings
from src.core.exceptions import (
    AgentUnavailableError,
    ContentModerationError,
    DelegationDepthError,
    ForbiddenError,
    MarketplaceError,
    NotFoundError,
    QuotaExceededError,
)
from src.models.agent import Agent, AgentStatus
from src.models.skill import AgentSkill
from src.models.task import Task, TaskStatus
from src.schemas.task import TaskCreate, TaskMessage, TaskRating
from src.services.credit_ledger import CreditLedgerService

logger = logging.getLogger(__name__)


class TaskBrokerService:
    """Orchestrates task lifecycle between client and provider agents."""

    # Shared rate limiter for quota RPM enforcement (class-level singleton)
    _quota_limiters: dict[str, "RateLimiter"] = {}

    # Terminal task states (no further transitions allowed)
    TERMINAL_STATUSES = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED}
    _TERMINAL_VALUES = {"completed", "failed", "canceled"}

    @staticmethod
    def _is_terminal(status) -> bool:
        """Check if a status is terminal, handling both enum and string values."""
        if hasattr(status, "value"):
            return status.value in TaskBrokerService._TERMINAL_VALUES
        return str(status) in TaskBrokerService._TERMINAL_VALUES

    @staticmethod
    def _status_value(status) -> str:
        """Get the string value of a status, handling both enum and string."""
        return status.value if hasattr(status, "value") else str(status)

    def __init__(self, db: AsyncSession):
        self.db = db
        self.credit_ledger = CreditLedgerService(db)

    @property
    def _use_pgvector(self) -> bool:
        """Check if the session's engine supports pgvector (PostgreSQL)."""
        url = str(self.db.get_bind().url)
        return "postgresql" in url or "asyncpg" in url

    # ------------------------------------------------------------------
    # Create task
    # ------------------------------------------------------------------

    async def create_task(
        self, data: TaskCreate, user_id: UUID, client_agent_id: UUID | None = None
    ) -> Task:
        """Create a new task.

        Steps:
            1. Verify provider agent exists and is active.
            2. Verify skill exists on provider.
            3. Get credit quote from agent pricing.
            4. Reserve credits from client's account.
            5. Create task record with status=submitted.
            6. Return task.
        """
        # 0a. Abuse detection — rate limit task creation per user
        from src.services.abuse_detector import check_task_creation_rate
        check_task_creation_rate(str(user_id))

        # 0b. Content moderation — check input messages
        from src.services.content_filter import check_input
        for msg in data.messages:
            for part in msg.parts or []:
                text = part.content if hasattr(part, "content") else (part.get("content") if isinstance(part, dict) else None)
                if text:
                    check_input(text)

        # 0c. Circuit breaker check
        from src.services.health_monitor import is_circuit_open
        if is_circuit_open(str(data.provider_agent_id)):
            raise AgentUnavailableError(
                detail=f"Agent {data.provider_agent_id} is temporarily unavailable due to recent failures"
            )

        # 0d. Delegation depth check
        if client_agent_id:
            depth = await self._resolve_delegation_depth(data.parent_task_id)
            if depth >= settings.max_delegation_depth:
                raise DelegationDepthError(
                    detail=f"Maximum delegation depth of {settings.max_delegation_depth} exceeded"
                )

        # 1. Verify provider
        provider = await self._get_active_agent(data.provider_agent_id)

        # 2. Verify skill
        skill = await self._get_skill_on_agent(data.skill_id, provider.id)

        # 2b. Resolve tier and enforce quotas
        tier = self._resolve_tier(provider, data.tier)
        if tier:
            await self._enforce_quota(
                user_id=user_id,
                provider_agent_id=provider.id,
                tier=tier,
                messages=data.messages,
            )

        # 3. Determine payment method
        payment_method = data.payment_method.value if data.payment_method else "credits"

        # 3a. Validate agent accepts this payment method
        accepted = provider.accepted_payment_methods or ["credits"]
        if payment_method not in accepted:
            raise MarketplaceError(
                status_code=400,
                detail=f"Agent does not accept '{payment_method}' payments. "
                       f"Accepted: {', '.join(accepted)}"
            )

        # 3b. Quote credits (used as price reference for both payment methods)
        credits_quoted = Decimal(str(
            self._resolve_credits(provider, data.max_credits, skill.avg_credits, data.tier)
        ))

        # 3c. High-cost approval gate
        if (
            float(credits_quoted) > settings.high_cost_approval_threshold
            and not data.confirmed
        ):
            # Create task in pending_approval state without reserving credits
            now = datetime.now(timezone.utc)
            task = Task(
                creator_user_id=user_id,
                client_agent_id=client_agent_id,
                provider_agent_id=provider.id,
                skill_id=skill.id,
                status=TaskStatus.PENDING_APPROVAL,
                messages=[m.model_dump() for m in data.messages],
                artifacts=[],
                credits_quoted=credits_quoted,
                payment_method=payment_method,
                suggested_agent_id=data.suggested_agent_id,
                suggestion_confidence=data.suggestion_confidence,
                status_history=[{"status": "pending_approval", "at": now.isoformat()}],
            )
            self.db.add(task)
            await self.db.commit()
            await self.db.refresh(task)
            return task

        # 3d. Handle payment based on method
        if payment_method == "credits":
            if credits_quoted > 0:
                await self.credit_ledger.reserve_credits(
                    owner_id=user_id,
                    amount=float(credits_quoted),
                    task_id=None,  # task not created yet; updated after creation
                )
            initial_status = TaskStatus.SUBMITTED
        else:
            # x402: no credit reservation, task starts as pending_payment
            initial_status = TaskStatus.PENDING_PAYMENT

        # 4. Create task
        now = datetime.now(timezone.utc)
        depth = await self._resolve_delegation_depth(data.parent_task_id) if client_agent_id else 0
        task = Task(
            creator_user_id=user_id,
            client_agent_id=client_agent_id,
            provider_agent_id=provider.id,
            skill_id=skill.id,
            status=initial_status,
            messages=[m.model_dump() for m in data.messages],
            artifacts=[],
            credits_quoted=credits_quoted,
            payment_method=payment_method,
            delegation_depth=depth,
            parent_task_id=data.parent_task_id,
            suggested_agent_id=data.suggested_agent_id,
            suggestion_confidence=data.suggestion_confidence,
            status_history=[{"status": initial_status.value, "at": now.isoformat()}],
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)

        # Dispatch task to the agent's A2A endpoint in the background.
        # Skip in test mode — agent endpoints are unreachable and background
        # tasks cause race conditions with test assertions.
        _in_tests = "pytest" in sys.modules
        if initial_status == TaskStatus.SUBMITTED and provider.endpoint and not _in_tests:
            grace = settings.task_grace_period_seconds
            asyncio.create_task(
                self._dispatch_with_grace_period(
                    task_id=task.id,
                    agent_endpoint=provider.endpoint,
                    skill_id=skill.skill_key,
                    messages=[m.model_dump() for m in data.messages],
                    provider_agent_id=provider.id,
                    grace_seconds=grace,
                )
            )

        return task

    # ------------------------------------------------------------------
    # Delegation suggestion
    # ------------------------------------------------------------------

    async def suggest_delegation(
        self,
        message: str,
        category: str | None = None,
        tags: list[str] | None = None,
        max_credits: float | None = None,
        limit: int = 3,
        user_llm_keys: dict[str, str] | None = None,
        user_id: str | None = None,
        account_tier: str = "free",
    ):
        """Suggest the best (agent, skill) pairs for a given message.

        Uses semantic search when an embedding API key is available,
        otherwise falls back to keyword matching.
        """
        from src.core.embeddings import EmbeddingService, MissingAPIKeyError
        from src.schemas.agent import AgentResponse, SkillResponse
        from src.schemas.suggestion import SkillSuggestion, SuggestionResponse

        # Try semantic search first
        fallback_used = False
        hint = None
        try:
            provider = settings.embedding_provider.lower()
            api_key = (user_llm_keys or {}).get(provider)
            embeddings = EmbeddingService(
                api_key=api_key, user_id=user_id, account_tier=account_tier,
            )
            query_embedding = await embeddings.generate(message)

            if self._use_pgvector:
                scored = await self._score_skills_db(
                    query_embedding, max_credits, category, tags, limit,
                )
            else:
                agents = await self._fetch_agents_with_embeddings(category, tags)
                scored = self._score_skills_python(agents, query_embedding, max_credits)
        except MissingAPIKeyError:
            logger.info("No embedding API key — falling back to keyword suggestion")
            agents = await self._fetch_agents(category, tags)
            scored = self._score_skills_keyword(agents, message, max_credits)
            fallback_used = True
            hint = "Configure an API key in Settings > LLM Keys for smarter suggestions."

        if not scored and not fallback_used:
            return SuggestionResponse(suggestions=[], hint="No active agents found.")

        # Sort by score descending and take top N
        scored.sort(key=lambda x: x[2], reverse=True)
        suggestions = []
        for agent_obj, skill_obj, score in scored[:limit]:
            suggestions.append(SkillSuggestion(
                agent=AgentResponse.model_validate(agent_obj),
                skill=SkillResponse.model_validate(skill_obj),
                confidence=round(score, 4),
                reason=self._build_reason(score, fallback_used),
                low_confidence=score < 0.3,
            ))

        return SuggestionResponse(
            suggestions=suggestions,
            fallback_used=fallback_used,
            hint=hint,
        )

    async def _fetch_agents(
        self, category: str | None, tags: list[str] | None,
    ) -> list[Agent]:
        """Fetch active agents with skills (no embeddings)."""
        stmt = (
            select(Agent)
            .options(selectinload(Agent.skills))
            .where(Agent.status == AgentStatus.ACTIVE)
        )
        if category:
            stmt = stmt.where(Agent.category == category)
        if tags:
            stmt = stmt.where(Agent.tags.contains(tags))
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    async def _fetch_agents_with_embeddings(
        self, category: str | None, tags: list[str] | None,
    ) -> list[Agent]:
        """Fetch active agents with skills including embeddings (SQLite path)."""
        stmt = (
            select(Agent)
            .options(selectinload(Agent.skills).undefer(AgentSkill.embedding))
            .where(Agent.status == AgentStatus.ACTIVE)
        )
        if category:
            stmt = stmt.where(Agent.category == category)
        if tags:
            stmt = stmt.where(Agent.tags.contains(tags))
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    async def _score_skills_db(
        self,
        query_embedding: list[float],
        max_credits: float | None,
        category: str | None,
        tags: list[str] | None,
        limit: int,
    ) -> list[tuple[Agent, AgentSkill, float]]:
        """DB-side scoring using pgvector cosine distance. Returns (agent, skill, similarity)."""
        # Query: each (agent, skill) pair with cosine similarity, ordered by best match
        similarity = (1 - AgentSkill.embedding.cosine_distance(query_embedding)).label("similarity")
        stmt = (
            select(Agent, AgentSkill, similarity)
            .join(AgentSkill, AgentSkill.agent_id == Agent.id)
            .where(Agent.status == AgentStatus.ACTIVE)
            .where(AgentSkill.embedding.isnot(None))
        )
        if max_credits is not None:
            stmt = stmt.where(
                (AgentSkill.avg_credits.is_(None)) | (AgentSkill.avg_credits <= max_credits)
            )
        if category:
            stmt = stmt.where(Agent.category == category)
        if tags:
            stmt = stmt.where(Agent.tags.contains(tags))
        stmt = stmt.order_by(AgentSkill.embedding.cosine_distance(query_embedding))
        stmt = stmt.limit(limit * 3)  # over-fetch to allow dedup per agent

        result = await self.db.execute(stmt)
        rows = result.all()

        # Ensure agents have skills loaded for response serialization
        scored = []
        for agent, skill, sim_score in rows:
            # Trigger skill loading via selectinload if not already loaded
            if not agent.skills:
                await self.db.refresh(agent, ["skills"])
            scored.append((agent, skill, float(sim_score)))
        return scored

    @staticmethod
    def _score_skills_python(
        agents: list[Agent],
        query_embedding: list[float],
        max_credits: float | None,
    ) -> list[tuple[Agent, AgentSkill, float]]:
        """In-memory scoring fallback for SQLite."""
        from src.services.discovery import DiscoveryService

        scored = []
        for agent in agents:
            for skill in agent.skills:
                if max_credits is not None and skill.avg_credits and skill.avg_credits > max_credits:
                    continue
                if skill.embedding is not None:
                    sim = DiscoveryService._cosine_similarity(query_embedding, list(skill.embedding))
                    scored.append((agent, skill, sim))
        return scored

    @staticmethod
    def _score_skills_keyword(
        agents: list[Agent],
        message: str,
        max_credits: float | None,
    ) -> list[tuple[Agent, AgentSkill, float]]:
        """Score each (agent, skill) pair by keyword overlap."""
        words = set(message.lower().split())
        scored = []
        for agent in agents:
            for skill in agent.skills:
                if max_credits is not None and skill.avg_credits and skill.avg_credits > max_credits:
                    continue
                skill_text = f"{skill.name} {skill.description}".lower()
                skill_words = set(skill_text.split())
                overlap = len(words & skill_words)
                if overlap > 0:
                    score = min(overlap / max(len(words), 1), 1.0)
                    scored.append((agent, skill, score))
        return scored

    async def check_skill_mismatch(
        self,
        messages: list,
        skill_id: str,
        agent_id: UUID,
        threshold: float = 0.4,
    ) -> str | None:
        """Check if a message aligns with the selected skill.

        Returns a warning string if similarity is below threshold, None otherwise.
        Silently returns None if embeddings are unavailable.
        """
        from src.core.embeddings import EmbeddingService, MissingAPIKeyError

        skill = await self._get_skill_on_agent(skill_id, agent_id)
        use_db = self._use_pgvector

        # On SQLite, load the deferred embedding for Python-side cosine sim
        skill_embedding = None
        if not use_db:
            stmt = select(AgentSkill.embedding).where(AgentSkill.id == skill.id)
            skill_embedding = (await self.db.execute(stmt)).scalar_one_or_none()
            if skill_embedding is None:
                return None

        # Extract text from messages
        text_parts = []
        for m in messages:
            msg = m if isinstance(m, dict) else m.model_dump()
            for part in msg.get("parts", []):
                if part.get("type") == "text" and part.get("content"):
                    text_parts.append(part["content"])
        if not text_parts:
            return None

        text = " ".join(text_parts)
        try:
            embeddings = EmbeddingService()
            query_embedding = await embeddings.generate(text)
        except (MissingAPIKeyError, Exception):
            return None

        # Compute similarity: DB-side on PG, Python-side on SQLite
        if use_db:
            stmt = select(
                (1 - AgentSkill.embedding.cosine_distance(query_embedding)).label("similarity")
            ).where(AgentSkill.id == skill.id)
            result = await self.db.execute(stmt)
            row = result.scalar_one_or_none()
            similarity = float(row) if row is not None else 0.0
        else:
            from src.services.discovery import DiscoveryService
            similarity = DiscoveryService._cosine_similarity(query_embedding, list(skill_embedding))

        if similarity < threshold:
            return (
                f"Your message may not match the selected skill '{skill.name}' "
                f"(confidence: {similarity:.0%}). Consider trying auto-delegation."
            )
        return None

    @staticmethod
    def _build_reason(score: float, fallback: bool) -> str:
        method = "keyword match" if fallback else "semantic similarity"
        if score >= 0.7:
            return f"Strong match via {method}"
        if score >= 0.3:
            return f"Moderate match via {method}"
        return f"Weak match via {method}"

    # ------------------------------------------------------------------
    # A2A dispatch (background)
    # ------------------------------------------------------------------

    @staticmethod
    async def _dispatch_with_grace_period(
        task_id: UUID,
        agent_endpoint: str,
        skill_id: str,
        messages: list[dict],
        provider_agent_id: UUID | None = None,
        grace_seconds: int = 5,
    ) -> None:
        """Wait for grace period, then dispatch if task hasn't been canceled."""
        from src.database import async_session

        if grace_seconds > 0:
            await asyncio.sleep(grace_seconds)

            # Re-check task status — user may have canceled during grace period
            try:
                async with async_session() as db:
                    broker = TaskBrokerService(db)
                    task = await broker.get_task(task_id)
                    if broker._is_terminal(task.status):
                        logger.info(
                            "Task %s canceled during grace period (status=%s), skipping dispatch",
                            task_id, broker._status_value(task.status),
                        )
                        return
            except Exception:
                logger.exception("Failed to check task %s status after grace period", task_id)
                return

        await TaskBrokerService._dispatch_to_agent(
            task_id=task_id,
            agent_endpoint=agent_endpoint,
            skill_id=skill_id,
            messages=messages,
            provider_agent_id=provider_agent_id,
        )

    @staticmethod
    async def _dispatch_to_agent(
        task_id: UUID,
        agent_endpoint: str,
        skill_id: str,
        messages: list[dict],
        provider_agent_id: UUID | None = None,
    ) -> None:
        """Call the agent's A2A endpoint and update the task with the result.

        Runs as a background task after create_task returns. If the agent
        responds synchronously with a completed result, we update the task
        status and artifacts. On failure, the task status is set to 'failed'.
        """
        from src.database import async_session
        from src.services.a2a_gateway import A2AGatewayService
        from src.services.health_monitor import record_circuit_failure, reset_circuit

        agent_id_str = str(provider_agent_id) if provider_agent_id else None

        try:
            async with async_session() as db:
                gateway = A2AGatewayService(db)
                response = await gateway.send_task(
                    agent_endpoint=agent_endpoint.rstrip("/") + "/",
                    task_data={
                        "id": str(task_id),
                        "skill_id": skill_id,
                        "messages": messages,
                    },
                )

                result = response.get("result", {})
                agent_status = result.get("status", {}).get("state")
                artifacts = result.get("artifacts", [])

                broker = TaskBrokerService(db)

                # Re-fetch task to check current status; skip if already terminal
                # (task may have been canceled/completed by another path)
                task = await broker.get_task(task_id)
                if broker._is_terminal(task.status):
                    logger.info(
                        "Task %s already in terminal state '%s', skipping dispatch update",
                        task_id, broker._status_value(task.status),
                    )
                    return

                if agent_status == "completed" and artifacts:
                    # Content moderation on output
                    try:
                        from src.services.content_filter import check_output
                        for artifact in artifacts:
                            for part in artifact.get("parts", []):
                                if isinstance(part, dict) and part.get("text"):
                                    check_output(part["text"])
                    except ContentModerationError:
                        logger.warning("Task %s output blocked by content moderation", task_id)
                        await broker.update_task_status(task_id, TaskStatus.FAILED)
                        return

                    await broker.update_task_status(
                        task_id, TaskStatus.COMPLETED, artifacts=artifacts
                    )
                    if agent_id_str:
                        reset_circuit(agent_id_str)
                elif agent_status == "failed":
                    await broker.update_task_status(task_id, TaskStatus.FAILED)
                    if agent_id_str:
                        record_circuit_failure(agent_id_str)
                elif "error" in response:
                    logger.warning(
                        "A2A dispatch error for task %s: %s",
                        task_id, response["error"],
                    )
                    await broker.update_task_status(task_id, TaskStatus.FAILED)
                    if agent_id_str:
                        record_circuit_failure(agent_id_str)

        except Exception:
            logger.exception("A2A dispatch failed for task %s to %s", task_id, agent_endpoint)
            if agent_id_str:
                record_circuit_failure(agent_id_str)
            try:
                async with async_session() as db:
                    broker = TaskBrokerService(db)
                    task = await broker.get_task(task_id)
                    if broker._is_terminal(task.status):
                        return
                    await broker.update_task_status(task_id, TaskStatus.FAILED)
            except Exception:
                logger.exception("Failed to mark task %s as failed", task_id)

    # ------------------------------------------------------------------
    # Get task
    # ------------------------------------------------------------------

    async def get_task(self, task_id: UUID, user_id: UUID | None = None) -> Task:
        """Get a task by ID, optionally enforcing ownership.

        When user_id is provided, verifies the user owns either the client
        or provider agent on the task.
        """
        stmt = (
            select(Task)
            .options(
                selectinload(Task.client_agent),
                selectinload(Task.provider_agent),
                selectinload(Task.skill),
            )
            .where(Task.id == task_id)
        )
        result = await self.db.execute(stmt)
        task = result.scalars().first()
        if not task:
            raise NotFoundError(detail=f"Task {task_id} not found")

        if user_id is not None:
            is_creator = task.creator_user_id == user_id
            owns_client = task.client_agent and task.client_agent.owner_id == user_id
            owns_provider = task.provider_agent and task.provider_agent.owner_id == user_id
            if not is_creator and not owns_client and not owns_provider:
                raise ForbiddenError(detail="You do not have access to this task")

        return task

    # ------------------------------------------------------------------
    # List tasks
    # ------------------------------------------------------------------

    async def list_tasks(
        self,
        agent_id: UUID | None = None,
        user_id: UUID | None = None,
        status: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Task], int]:
        """List tasks with optional filters, paginated."""
        stmt = select(Task).options(
            selectinload(Task.client_agent),
            selectinload(Task.provider_agent),
            selectinload(Task.skill),
        )

        if agent_id:
            stmt = stmt.where(
                (Task.client_agent_id == agent_id)
                | (Task.provider_agent_id == agent_id)
            )
        if user_id:
            # Tasks where the user is the creator, or owns the client/provider agent.
            from sqlalchemy import or_
            owned_ids_sq = select(Agent.id).where(Agent.owner_id == user_id).subquery()
            stmt = stmt.where(
                or_(
                    Task.creator_user_id == user_id,
                    Task.client_agent_id.in_(select(owned_ids_sq.c.id)),
                    Task.provider_agent_id.in_(select(owned_ids_sq.c.id)),
                )
            )
        if status:
            stmt = stmt.where(Task.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        offset = (page - 1) * per_page
        stmt = stmt.offset(offset).limit(per_page).order_by(Task.created_at.desc())
        result = await self.db.execute(stmt)
        tasks = list(result.scalars().unique().all())

        return tasks, total

    # ------------------------------------------------------------------
    # Send message
    # ------------------------------------------------------------------

    async def send_message(self, task_id: UUID, message: TaskMessage, user_id: UUID | None = None) -> Task:
        """Append a message to the task's messages JSONB array."""
        task = await self.get_task(task_id, user_id=user_id)
        messages = list(task.messages or [])
        messages.append(message.model_dump())
        task.messages = messages

        # If the provider sends a message while status is submitted, move to working
        if message.role == "agent" and task.status == TaskStatus.SUBMITTED:
            task.status = TaskStatus.WORKING

        await self.db.commit()
        await self.db.refresh(task)
        return task

    # ------------------------------------------------------------------
    # Update status
    # ------------------------------------------------------------------

    async def update_task_status(
        self,
        task_id: UUID,
        status: TaskStatus,
        artifacts: list | None = None,
    ) -> Task:
        """Update task status. Handle credit settlement on completion or failure."""
        task = await self.get_task(task_id)

        # Don't overwrite tasks already in a terminal state
        if self._is_terminal(task.status):
            logger.info(
                "Skipping status update for task %s: already in terminal state '%s'",
                task_id, self._status_value(task.status),
            )
            return task

        # Append to status history
        now_iso = datetime.now(timezone.utc).isoformat()
        history = list(task.status_history or [])
        history.append({"status": status.value, "at": now_iso})
        task.status_history = history

        task.status = status

        if artifacts:
            task.artifacts = artifacts

        now = datetime.now(timezone.utc)

        if status == TaskStatus.COMPLETED:
            task.completed_at = now
            # Calculate latency
            if task.created_at:
                created = task.created_at
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                delta = now - created
                task.latency_ms = int(delta.total_seconds() * 1000)

            # Charge credits
            quoted = float(task.credits_quoted or 0)
            if quoted > 0 and task.client_agent and task.provider_agent:
                # A2A delegation: client agent owner pays provider agent owner
                if task.payment_method == "credits":
                    await self.credit_ledger.charge_credits(
                        client_owner_id=task.client_agent.owner_id,
                        provider_owner_id=task.provider_agent.owner_id,
                        amount=quoted,
                        task_id=task.id,
                    )
                    task.credits_charged = Decimal(str(quoted))
                elif task.payment_method == "x402":
                    # x402: payment already settled on-chain
                    task.credits_charged = Decimal(str(quoted))
            elif quoted > 0 and not task.client_agent_id and task.provider_agent:
                # User-initiated task: creator_user_id pays provider agent owner
                if task.payment_method == "credits" and task.creator_user_id:
                    await self.credit_ledger.charge_credits(
                        client_owner_id=task.creator_user_id,
                        provider_owner_id=task.provider_agent.owner_id,
                        amount=quoted,
                        task_id=task.id,
                    )
                    task.credits_charged = Decimal(str(quoted))
                elif task.payment_method == "x402":
                    task.credits_charged = Decimal(str(quoted))

            # Update provider stats
            if task.provider_agent:
                await self._update_provider_stats(task.provider_agent)

            # Trigger quality scoring and reputation update in background
            _in_tests = "pytest" in sys.modules
            if not _in_tests:
                asyncio.create_task(
                    self._run_eval_and_reputation(task.id, task.provider_agent_id)
                )

        elif status == TaskStatus.FAILED:
            # Release reserved credits
            quoted = float(task.credits_quoted or 0)
            if quoted > 0 and task.client_agent:
                # A2A delegation: release from client agent owner
                if task.payment_method == "credits":
                    await self.credit_ledger.release_credits(
                        owner_id=task.client_agent.owner_id,
                        amount=quoted,
                        task_id=task.id,
                    )
            elif quoted > 0 and not task.client_agent_id and task.creator_user_id:
                # User-initiated task: release from creator user
                if task.payment_method == "credits":
                    await self.credit_ledger.release_credits(
                        owner_id=task.creator_user_id,
                        amount=quoted,
                        task_id=task.id,
                    )

        await self.db.commit()
        await self.db.refresh(task)

        # Fire push notification if callback_url is set
        if getattr(task, "callback_url", None):
            from src.services.push_notifier import send_push_notification
            asyncio.create_task(
                send_push_notification(
                    callback_url=task.callback_url,
                    task_id=str(task.id),
                    status=task.status.value if hasattr(task.status, "value") else task.status,
                    artifacts=task.artifacts,
                )
            )

        return task

    # ------------------------------------------------------------------
    # Cancel task
    # ------------------------------------------------------------------

    async def cancel_task(self, task_id: UUID, user_id: UUID) -> Task:
        """Cancel a task and release reserved credits."""
        task = await self.get_task(task_id, user_id=user_id)

        # Verify the user owns the client agent
        if task.client_agent and task.client_agent.owner_id != user_id:
            raise ForbiddenError(detail="You do not own the client agent for this task")

        # Guard: only cancel tasks that are still in progress
        if self._is_terminal(task.status):
            raise ForbiddenError(
                detail=f"Cannot cancel task in '{self._status_value(task.status)}' state"
            )

        task.status = TaskStatus.CANCELED

        # Append to status history
        from datetime import datetime, timezone
        history = list(task.status_history or [])
        history.append({"status": "canceled", "at": datetime.now(timezone.utc).isoformat()})
        task.status_history = history

        quoted = float(task.credits_quoted or 0)
        if quoted > 0 and task.client_agent:
            if task.payment_method == "credits":
                await self.credit_ledger.release_credits(
                    owner_id=task.client_agent.owner_id,
                    amount=quoted,
                    task_id=task.id,
                )

        await self.db.commit()
        await self.db.refresh(task)
        return task

    # ------------------------------------------------------------------
    # Confirm high-cost task
    # ------------------------------------------------------------------

    async def confirm_task(self, task_id: UUID, user_id: UUID) -> Task:
        """Confirm a pending_approval task — reserve credits and dispatch."""
        task = await self.get_task(task_id, user_id=user_id)

        status_val = self._status_value(task.status)
        if status_val != "pending_approval":
            raise ForbiddenError(
                detail=f"Can only confirm tasks in 'pending_approval' state, got '{status_val}'"
            )

        # Reserve credits
        quoted = float(task.credits_quoted or 0)
        if quoted > 0 and task.payment_method == "credits":
            await self.credit_ledger.reserve_credits(
                owner_id=user_id,
                amount=quoted,
                task_id=task.id,
            )

        # Transition to submitted
        task.status = TaskStatus.SUBMITTED
        history = list(task.status_history or [])
        history.append({"status": "submitted", "at": datetime.now(timezone.utc).isoformat()})
        task.status_history = history

        await self.db.commit()
        await self.db.refresh(task)

        # Dispatch (no grace period for confirmed tasks — user already approved)
        provider = task.provider_agent
        skill = task.skill
        _in_tests = "pytest" in sys.modules
        if provider and provider.endpoint and skill and not _in_tests:
            asyncio.create_task(
                self._dispatch_to_agent(
                    task_id=task.id,
                    agent_endpoint=provider.endpoint,
                    skill_id=skill.skill_key,
                    messages=list(task.messages or []),
                    provider_agent_id=provider.id,
                )
            )

        return task

    # ------------------------------------------------------------------
    # Rate task
    # ------------------------------------------------------------------

    async def rate_task(
        self, task_id: UUID, rating: TaskRating, user_id: UUID
    ) -> Task:
        """Set client rating and update provider agent reputation."""
        task = await self.get_task(task_id)

        if task.client_agent and task.client_agent.owner_id != user_id:
            raise ForbiddenError(detail="Only the client can rate this task")

        if task.status != TaskStatus.COMPLETED:
            raise ForbiddenError(detail="Can only rate completed tasks")

        task.client_rating = rating.score

        # Recalculate provider reputation
        if task.provider_agent:
            await self._update_provider_stats(task.provider_agent)

        await self.db.commit()
        await self.db.refresh(task)
        return task

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_active_agent(self, agent_id: UUID) -> Agent:
        """Fetch an agent and verify it is active."""
        stmt = select(Agent).where(Agent.id == agent_id)
        result = await self.db.execute(stmt)
        agent = result.scalars().first()
        if not agent:
            raise NotFoundError(detail=f"Agent {agent_id} not found")
        if agent.status != AgentStatus.ACTIVE:
            raise NotFoundError(detail=f"Agent {agent_id} is not active")
        return agent

    async def _get_skill_on_agent(self, skill_id: str, agent_id: UUID) -> AgentSkill:
        """Verify that a skill belongs to the specified agent."""
        # Try to parse as UUID; if it fails, only match by skill_key
        try:
            skill_uuid = UUID(skill_id)
            skill_filter = (AgentSkill.skill_key == skill_id) | (AgentSkill.id == skill_uuid)
        except (ValueError, AttributeError):
            skill_filter = AgentSkill.skill_key == skill_id
        stmt = select(AgentSkill).where(
            AgentSkill.agent_id == agent_id,
            skill_filter,
        )
        result = await self.db.execute(stmt)
        skill = result.scalars().first()
        if not skill:
            raise NotFoundError(
                detail=f"Skill {skill_id} not found on agent {agent_id}"
            )
        return skill

    # ------------------------------------------------------------------
    # Quota enforcement
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_tier(provider: Agent, tier_name: str | None = None) -> dict | None:
        """Find the applicable pricing tier for this request."""
        pricing = provider.pricing or {}
        tiers = pricing.get("tiers", [])
        if not tiers:
            return None

        if tier_name:
            selected = next(
                (t for t in tiers if t.get("name", "").lower() == tier_name.lower()),
                None,
            )
            if selected:
                return selected

        # Default tier, or first tier
        return next(
            (t for t in tiers if t.get("is_default")),
            tiers[0],
        )

    async def _enforce_quota(
        self,
        user_id: UUID,
        provider_agent_id: UUID,
        tier: dict,
        messages: list | None = None,
    ) -> None:
        """Check usage against the tier's quota limits.

        Raises QuotaExceededError if any limit is breached.
        """
        quota = tier.get("quota")
        if not quota:
            return

        tier_name = tier.get("name", "default")
        now = datetime.now(timezone.utc)

        # Find agents owned by this user (to count their tasks)
        owned_agent_ids = await self._get_user_agent_ids(user_id)
        if not owned_agent_ids:
            return  # No agents = no prior tasks to count

        # Daily task limit
        daily_limit = quota.get("daily_tasks")
        if daily_limit is not None:
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            daily_count = await self._count_tasks(
                client_agent_ids=owned_agent_ids,
                provider_agent_id=provider_agent_id,
                since=start_of_day,
            )
            if daily_count >= daily_limit:
                raise QuotaExceededError(
                    detail=f"Daily task limit reached for '{tier_name}' tier "
                    f"({daily_count}/{daily_limit} tasks today)"
                )

        # Monthly task limit
        monthly_limit = quota.get("monthly_tasks")
        if monthly_limit is not None:
            start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_count = await self._count_tasks(
                client_agent_ids=owned_agent_ids,
                provider_agent_id=provider_agent_id,
                since=start_of_month,
            )
            if monthly_count >= monthly_limit:
                raise QuotaExceededError(
                    detail=f"Monthly task limit reached for '{tier_name}' tier "
                    f"({monthly_count}/{monthly_limit} tasks this month)"
                )

        # Per-minute rate limit
        rpm_limit = quota.get("rate_limit_rpm")
        if rpm_limit is not None:
            from src.core.rate_limiter import RateLimiter
            key = f"quota:{user_id}:{provider_agent_id}"
            if key not in TaskBrokerService._quota_limiters:
                TaskBrokerService._quota_limiters[key] = RateLimiter(
                    max_requests=rpm_limit, window_seconds=60
                )
            if not TaskBrokerService._quota_limiters[key].check(key):
                raise QuotaExceededError(
                    detail=f"Rate limit exceeded for '{tier_name}' tier "
                    f"({rpm_limit} requests/minute)"
                )

        # Max tokens per task (rough check on message content length)
        max_tokens = quota.get("max_tokens_per_task")
        if max_tokens is not None and messages:
            total_chars = sum(
                len(p.content or "")
                for m in messages
                for p in m.parts
            )
            # Rough estimate: 1 token ≈ 4 characters
            estimated_tokens = total_chars // 4
            if estimated_tokens > max_tokens:
                raise QuotaExceededError(
                    detail=f"Input exceeds max tokens for '{tier_name}' tier "
                    f"(~{estimated_tokens} tokens, limit {max_tokens})"
                )

    async def _get_user_agent_ids(self, user_id: UUID) -> list[UUID]:
        """Get all agent IDs owned by a user."""
        stmt = select(Agent.id).where(Agent.owner_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _count_tasks(
        self,
        client_agent_ids: list[UUID],
        provider_agent_id: UUID,
        since: datetime,
    ) -> int:
        """Count tasks created by any of the client agents against a specific provider."""
        if not client_agent_ids:
            return 0
        stmt = select(func.count()).where(
            Task.client_agent_id.in_(client_agent_ids),
            Task.provider_agent_id == provider_agent_id,
            Task.created_at >= since,
        )
        return (await self.db.execute(stmt)).scalar_one()

    # ------------------------------------------------------------------
    # Credit resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_credits(
        provider: Agent,
        max_credits: float | None,
        skill_avg_credits: float,
        tier_name: str | None = None,
    ) -> float:
        """Resolve the credit cost for a task.

        Resolution order:
            1. Client's explicit max_credits
            2. Requested tier's credits_per_unit (if tier_name given)
            3. Default pricing tier's credits_per_unit
            4. Legacy pricing.credits field
            5. Skill average credits
            6. Zero (free / open license)
        """
        if max_credits is not None and max_credits > 0:
            return max_credits

        pricing = provider.pricing or {}

        # Open license = always free
        if pricing.get("license_type") == "open":
            return 0

        # Try tiered pricing
        tiers = pricing.get("tiers", [])
        if tiers:
            selected = None
            if tier_name:
                selected = next(
                    (t for t in tiers if t.get("name", "").lower() == tier_name.lower()),
                    None,
                )
            if not selected:
                # Fall back to default tier, then first tier
                selected = next(
                    (t for t in tiers if t.get("is_default")),
                    tiers[0],
                )
            credits = selected.get("credits_per_unit", 0)
            if credits > 0:
                return credits

        # Legacy flat pricing
        legacy_credits = pricing.get("credits", 0)
        if legacy_credits > 0:
            return legacy_credits

        # Skill average
        if skill_avg_credits > 0:
            return skill_avg_credits

        return 0

    # ------------------------------------------------------------------
    # Webhook handlers (called by provider agents via /webhooks/a2a)
    # ------------------------------------------------------------------

    async def handle_status_update(
        self, agent_id: UUID, params: dict
    ) -> dict:
        """Handle a tasks/statusUpdate callback from a provider agent.

        The provider sends this when a task's status changes (e.g.
        submitted → working → completed, or working → failed).

        Expected params:
            id: str          -- task UUID
            status: str      -- new status value
            artifacts: list  -- optional list of artifact dicts
        """
        task_id_str = params.get("id")
        new_status_str = params.get("status")

        if not task_id_str or not new_status_str:
            raise MarketplaceError(
                status_code=400,
                detail="Required: id and status in params",
            )

        task_id = UUID(task_id_str)
        task = await self.get_task(task_id)

        # Verify the callback is from the correct provider agent
        if task.provider_agent_id != agent_id:
            raise ForbiddenError(
                detail="Agent is not the provider for this task"
            )

        # Parse the new status
        try:
            new_status = TaskStatus(new_status_str)
        except ValueError:
            raise MarketplaceError(
                status_code=400,
                detail=f"Invalid status: {new_status_str}",
            )

        # Don't allow updates to tasks already in a terminal state
        if self._is_terminal(task.status):
            raise ForbiddenError(
                detail=f"Cannot update task in terminal state '{self._status_value(task.status)}'"
            )

        artifacts = params.get("artifacts")
        updated = await self.update_task_status(task_id, new_status, artifacts)
        return {
            "id": str(updated.id),
            "status": updated.status.value if hasattr(updated.status, "value") else updated.status,
        }

    async def handle_artifact_update(
        self, agent_id: UUID, params: dict
    ) -> dict:
        """Handle a tasks/artifactUpdate callback from a provider agent.

        Appends new artifacts to the task without changing its status.

        Expected params:
            id: str          -- task UUID
            artifacts: list  -- list of artifact dicts to append
        """
        task_id_str = params.get("id")
        new_artifacts = params.get("artifacts", [])

        if not task_id_str:
            raise MarketplaceError(
                status_code=400,
                detail="Required: id in params",
            )

        task_id = UUID(task_id_str)
        task = await self.get_task(task_id)

        # Verify the callback is from the correct provider agent
        if task.provider_agent_id != agent_id:
            raise ForbiddenError(
                detail="Agent is not the provider for this task"
            )

        # Append new artifacts
        existing = list(task.artifacts or [])
        existing.extend(new_artifacts)
        task.artifacts = existing

        await self.db.commit()
        await self.db.refresh(task)

        return {
            "id": str(task.id),
            "artifact_count": len(task.artifacts),
        }

    @staticmethod
    async def _run_eval_and_reputation(task_id: UUID, provider_agent_id: UUID | None) -> None:
        """Background: score the task quality, then update agent reputation."""
        from src.database import async_session

        try:
            async with async_session() as db:
                from src.services.eval_service import EvalService
                eval_svc = EvalService(db)
                await eval_svc.score_response(task_id)

                if provider_agent_id:
                    from src.services.reputation import ReputationService
                    rep_svc = ReputationService(db)
                    await rep_svc.update_reputation(provider_agent_id)
        except Exception:
            logger.exception("Eval/reputation update failed for task %s", task_id)

    async def _update_provider_stats(self, provider: Agent) -> None:
        """Recalculate total_tasks_completed, success_rate, and avg_latency_ms."""
        completed_count_stmt = select(func.count()).where(
            Task.provider_agent_id == provider.id,
            Task.status == TaskStatus.COMPLETED,
        )
        total_count_stmt = select(func.count()).where(
            Task.provider_agent_id == provider.id,
            Task.status.in_([
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELED,
            ]),
        )
        avg_latency_stmt = select(func.avg(Task.latency_ms)).where(
            Task.provider_agent_id == provider.id,
            Task.status == TaskStatus.COMPLETED,
            Task.latency_ms.isnot(None),
        )

        completed = (await self.db.execute(completed_count_stmt)).scalar_one()
        total = (await self.db.execute(total_count_stmt)).scalar_one()
        avg_lat = (await self.db.execute(avg_latency_stmt)).scalar_one()

        provider.total_tasks_completed = completed
        provider.success_rate = (completed / total) if total > 0 else 0.0
        provider.avg_latency_ms = float(avg_lat) if avg_lat else 0.0

    async def _resolve_delegation_depth(self, parent_task_id: UUID | None) -> int:
        """Look up delegation depth from parent task chain."""
        if not parent_task_id:
            return 0
        result = await self.db.execute(
            select(Task.delegation_depth).where(Task.id == parent_task_id)
        )
        parent_depth = result.scalar_one_or_none()
        return (parent_depth or 0) + 1
