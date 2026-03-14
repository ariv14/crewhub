"""Service for creating and managing community-created custom agents."""

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.exceptions import (
    MarketplaceError,
    NotFoundError,
    QuotaExceededError,
)
from src.models.custom_agent import (
    AgentRequest,
    CustomAgent,
    CustomAgentStatus,
    CustomAgentVote,
)
from src.services.credit_ledger import CreditLedgerService

logger = logging.getLogger(__name__)

# Meta-prompt for generating agent personas
_META_PROMPT = """\
A user needs help with: "{query}"

Design a specialist AI agent for this task. Output ONLY valid JSON (no markdown, no code fences):
{{
  "name": "...",
  "description": "...",
  "system_prompt": "...",
  "category": "...",
  "tags": [...]
}}

Rules:
- name: A friendly, professional title (e.g. "Grant Writing Specialist", "Python Tutor")
- description: One clear sentence explaining what this agent does
- system_prompt: 200-500 words defining the agent's expertise, tone, and approach. \
Be specific about domain knowledge, methodology, and communication style.
- category: One of: general, code, data, writing, research, design, automation, security, finance, support
- tags: 3-5 relevant keywords
"""


class CustomAgentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.credit_ledger = CreditLedgerService(db)

    async def create_agent(
        self,
        query: str,
        user_id: uuid.UUID,
        category: str | None = None,
        auto_execute: bool = True,
    ) -> dict:
        """Create a custom agent from a user's natural-language description.

        Returns dict with 'agent' (CustomAgent) and optionally 'task_id' + 'result'.
        """
        # Rate limit: max creations per day
        await self._check_daily_limit(user_id)

        # Reserve credits for creation
        cost = settings.custom_agent_create_cost
        await self.credit_ledger.reserve(user_id, cost, reason="Custom agent creation")

        try:
            # Generate persona via LLM
            persona = await self._generate_persona(query, category)

            # Create DB record
            agent = CustomAgent(
                name=persona["name"],
                description=persona["description"],
                system_prompt=persona["system_prompt"],
                category=persona.get("category", category or "general"),
                tags=persona.get("tags", []),
                source_query=query,
                status=CustomAgentStatus.active.value,
                created_by_user_id=user_id,
            )
            self.db.add(agent)
            await self.db.flush()

            result = {"agent": agent, "task_id": None, "result": None}

            # Auto-execute first task if requested
            if auto_execute:
                task_result = await self._execute_task(agent, query, user_id)
                result["task_id"] = task_result.get("task_id")
                result["result"] = task_result.get("result")

            # Charge credits (creation succeeded)
            await self.credit_ledger.charge(
                user_id, cost, reason=f"Created custom agent: {agent.name}"
            )

            return result

        except Exception:
            # Release reserved credits on failure
            await self.credit_ledger.release(user_id, cost, reason="Custom agent creation failed")
            raise

    async def try_custom_agent(
        self,
        custom_agent_id: uuid.UUID,
        message: str,
        user_id: uuid.UUID,
    ) -> dict:
        """Execute a task using a community-created custom agent."""
        agent = await self._get_agent(custom_agent_id)

        # Reserve credits
        cost = settings.custom_agent_try_cost
        await self.credit_ledger.reserve(user_id, cost, reason=f"Try custom agent: {agent.name}")

        try:
            result = await self._execute_task(agent, message, user_id)

            # Increment try count
            agent.try_count += 1
            await self.db.flush()

            # Charge credits
            await self.credit_ledger.charge(
                user_id, cost, reason=f"Tried custom agent: {agent.name}"
            )

            return result

        except Exception:
            await self.credit_ledger.release(
                user_id, cost, reason="Custom agent try failed"
            )
            raise

    async def list_agents(
        self,
        sort: str = "popular",
        category: str | None = None,
        page: int = 1,
        per_page: int = 20,
        user_id: uuid.UUID | None = None,
    ) -> dict:
        """List community agents with sorting and optional user vote info."""
        stmt = select(CustomAgent).where(
            CustomAgent.status != CustomAgentStatus.archived.value
        )

        if category:
            stmt = stmt.where(CustomAgent.category == category)

        # Sorting
        if sort == "popular":
            stmt = stmt.order_by(CustomAgent.upvote_count.desc(), CustomAgent.try_count.desc())
        elif sort == "tried":
            stmt = stmt.order_by(CustomAgent.try_count.desc())
        elif sort == "rated":
            stmt = stmt.order_by(CustomAgent.avg_rating.desc())
        else:  # "new"
            stmt = stmt.order_by(CustomAgent.created_at.desc())

        # Count total
        count_stmt = select(func.count()).select_from(
            stmt.subquery()
        )
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Paginate
        stmt = stmt.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(stmt)
        agents = list(result.scalars().all())

        # Attach user votes if authenticated
        if user_id and agents:
            agent_ids = [a.id for a in agents]
            vote_stmt = select(CustomAgentVote).where(
                CustomAgentVote.custom_agent_id.in_(agent_ids),
                CustomAgentVote.user_id == user_id,
            )
            votes = (await self.db.execute(vote_stmt)).scalars().all()
            vote_map = {v.custom_agent_id: v.vote for v in votes}
            for a in agents:
                a._user_vote = vote_map.get(a.id)
        else:
            for a in agents:
                a._user_vote = None

        return {"agents": agents, "total": total}

    async def get_agent(
        self, custom_agent_id: uuid.UUID, user_id: uuid.UUID | None = None
    ) -> CustomAgent:
        """Get a single custom agent with optional user vote."""
        agent = await self._get_agent(custom_agent_id)

        if user_id:
            vote_stmt = select(CustomAgentVote).where(
                CustomAgentVote.custom_agent_id == custom_agent_id,
                CustomAgentVote.user_id == user_id,
            )
            vote = (await self.db.execute(vote_stmt)).scalar_one_or_none()
            agent._user_vote = vote.vote if vote else None
        else:
            agent._user_vote = None

        return agent

    async def vote(
        self, custom_agent_id: uuid.UUID, user_id: uuid.UUID, vote_value: int
    ) -> CustomAgent:
        """Upvote (+1) or downvote (-1) a custom agent. Upserts."""
        if vote_value not in (1, -1):
            raise MarketplaceError(status_code=400, detail="Vote must be +1 or -1")

        agent = await self._get_agent(custom_agent_id)

        # Upsert vote
        existing = (
            await self.db.execute(
                select(CustomAgentVote).where(
                    CustomAgentVote.custom_agent_id == custom_agent_id,
                    CustomAgentVote.user_id == user_id,
                )
            )
        ).scalar_one_or_none()

        if existing:
            old_vote = existing.vote
            existing.vote = vote_value
            # Update aggregate: remove old, add new
            agent.upvote_count += vote_value - old_vote
        else:
            self.db.add(
                CustomAgentVote(
                    custom_agent_id=custom_agent_id,
                    user_id=user_id,
                    vote=vote_value,
                )
            )
            agent.upvote_count += vote_value

        await self.db.flush()
        agent._user_vote = vote_value
        return agent

    async def record_demand(
        self,
        query: str,
        confidence: float | None = None,
        user_id: uuid.UUID | None = None,
        custom_agent_id: uuid.UUID | None = None,
    ) -> None:
        """Record a demand signal (fire-and-forget for low-confidence searches)."""
        self.db.add(
            AgentRequest(
                user_id=user_id,
                query=query,
                best_match_confidence=confidence,
                custom_agent_id=custom_agent_id,
            )
        )
        await self.db.flush()

    async def list_requests(
        self, page: int = 1, per_page: int = 50
    ) -> dict:
        """List demand signals (admin only)."""
        stmt = select(AgentRequest).order_by(AgentRequest.created_at.desc())

        count_stmt = select(func.count()).select_from(AgentRequest)
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(stmt)
        requests = list(result.scalars().all())

        return {"requests": requests, "total": total}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_agent(self, custom_agent_id: uuid.UUID) -> CustomAgent:
        stmt = select(CustomAgent).where(CustomAgent.id == custom_agent_id)
        agent = (await self.db.execute(stmt)).scalar_one_or_none()
        if not agent:
            raise NotFoundError("Custom agent not found")
        return agent

    async def _check_daily_limit(self, user_id: uuid.UUID) -> None:
        """Enforce daily creation rate limit."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=1)
        stmt = (
            select(func.count())
            .select_from(CustomAgent)
            .where(
                CustomAgent.created_by_user_id == user_id,
                CustomAgent.created_at >= cutoff,
            )
        )
        count = (await self.db.execute(stmt)).scalar() or 0
        if count >= settings.custom_agent_daily_limit:
            raise QuotaExceededError(
                f"Daily custom agent limit reached ({settings.custom_agent_daily_limit}/day)"
            )

    async def _generate_persona(self, query: str, category: str | None) -> dict:
        """Call LLM to generate an agent persona from the user's query."""
        prompt = _META_PROMPT.format(query=query)
        if category:
            prompt += f"\nPreferred category: {category}"

        # Use Groq via LiteLLM (same as demo agents)
        groq_key = settings.platform_embedding_key  # Reuse platform key
        if not groq_key:
            import os
            groq_key = os.environ.get("GROQ_API_KEY", "")

        if not groq_key:
            # Fallback: generate a simple persona without LLM
            return self._fallback_persona(query, category)

        try:
            import litellm

            response = await litellm.acompletion(
                model="groq/llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are an AI agent designer. Output only valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                api_key=groq_key,
                timeout=30,
            )
            raw = response.choices[0].message.content.strip()

            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()

            persona = json.loads(raw)

            # Validate required fields
            for key in ("name", "description", "system_prompt"):
                if key not in persona or not persona[key]:
                    raise ValueError(f"Missing required field: {key}")

            return persona

        except Exception as exc:
            logger.warning("LLM persona generation failed: %s — using fallback", exc)
            return self._fallback_persona(query, category)

    def _fallback_persona(self, query: str, category: str | None) -> dict:
        """Generate a basic persona without LLM when API is unavailable."""
        # Extract a reasonable name from the query
        words = query.strip().split()
        name_words = words[:4] if len(words) > 4 else words
        name = " ".join(w.capitalize() for w in name_words) + " Specialist"

        return {
            "name": name,
            "description": f"A specialist agent created to help with: {query[:200]}",
            "system_prompt": (
                f"You are a helpful specialist assistant. A user needs help with the following:\n\n"
                f"{query}\n\n"
                f"Provide thorough, expert-level assistance. Be clear, structured, and actionable. "
                f"If the task requires specific domain knowledge, draw on best practices and "
                f"established methodologies. Always explain your reasoning."
            ),
            "category": category or "general",
            "tags": [w.lower() for w in words[:5] if len(w) > 3],
        }

    async def _execute_task(
        self, agent: CustomAgent, message: str, user_id: uuid.UUID
    ) -> dict:
        """Execute a task via the Creator Agent HF Space.

        Sends the custom agent's system_prompt as metadata so the Creator Agent
        can role-play as that specialist.
        """
        if not settings.creator_agent_id or not settings.creator_skill_id:
            # Creator Agent not configured — use inline LLM call
            return await self._execute_inline(agent, message)

        from src.schemas.task import TaskCreate, TaskMessage

        task_data = TaskCreate(
            provider_agent_id=settings.creator_agent_id,
            skill_id=settings.creator_skill_id,
            messages=[
                TaskMessage(
                    role="user",
                    parts=[{"type": "text", "content": message}],
                )
            ],
            metadata={"system_prompt": agent.system_prompt},
        )

        from src.services.task_broker import TaskBrokerService

        broker = TaskBrokerService(self.db)
        task = await broker.create_task(task_data, user_id)

        return {
            "task_id": str(task.id),
            "result": None,  # Result comes async via A2A callback
        }

    async def _execute_inline(self, agent: CustomAgent, message: str) -> dict:
        """Fallback: execute directly via LLM when Creator Agent isn't deployed."""
        import os

        groq_key = os.environ.get("GROQ_API_KEY", settings.platform_embedding_key)
        if not groq_key:
            return {
                "task_id": None,
                "result": "Agent created successfully but execution is unavailable (no LLM API key configured).",
            }

        try:
            import litellm

            response = await litellm.acompletion(
                model="groq/llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": agent.system_prompt},
                    {"role": "user", "content": message},
                ],
                api_key=groq_key,
                timeout=60,
            )
            result = response.choices[0].message.content

            # Increment completion count
            agent.completion_count += 1
            await self.db.flush()

            return {"task_id": None, "result": result}

        except Exception as exc:
            logger.warning("Inline execution failed: %s", exc)
            return {
                "task_id": None,
                "result": f"Agent created but execution failed: {exc}",
            }
