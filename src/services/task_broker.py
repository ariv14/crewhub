"""Task broker service -- create, manage, and rate tasks between agents."""

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import ForbiddenError, MarketplaceError, NotFoundError, QuotaExceededError
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

        # 3c. Handle payment based on method
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
            status_history=[{"status": initial_status.value, "at": now.isoformat()}],
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)

        # Dispatch task to the agent's A2A endpoint in the background
        if initial_status == TaskStatus.SUBMITTED and provider.endpoint:
            asyncio.create_task(
                self._dispatch_to_agent(
                    task_id=task.id,
                    agent_endpoint=provider.endpoint,
                    skill_id=data.skill_id,
                    messages=[m.model_dump() for m in data.messages],
                )
            )

        return task

    # ------------------------------------------------------------------
    # A2A dispatch (background)
    # ------------------------------------------------------------------

    @staticmethod
    async def _dispatch_to_agent(
        task_id: UUID,
        agent_endpoint: str,
        skill_id: str,
        messages: list[dict],
    ) -> None:
        """Call the agent's A2A endpoint and update the task with the result.

        Runs as a background task after create_task returns. If the agent
        responds synchronously with a completed result, we update the task
        status and artifacts. On failure, the task status is set to 'failed'.
        """
        from src.database import async_session
        from src.services.a2a_gateway import A2AGatewayService

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

                if agent_status == "completed" and artifacts:
                    await broker.update_task_status(
                        task_id, TaskStatus.COMPLETED, artifacts=artifacts
                    )
                elif agent_status == "failed":
                    await broker.update_task_status(task_id, TaskStatus.FAILED)
                elif "error" in response:
                    logger.warning(
                        "A2A dispatch error for task %s: %s",
                        task_id, response["error"],
                    )
                    await broker.update_task_status(task_id, TaskStatus.FAILED)

        except Exception:
            logger.exception("A2A dispatch failed for task %s to %s", task_id, agent_endpoint)
            try:
                async with async_session() as db:
                    broker = TaskBrokerService(db)
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

            # Update provider stats
            if task.provider_agent:
                await self._update_provider_stats(task.provider_agent)

        elif status == TaskStatus.FAILED:
            # Release reserved credits
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

        # Fire push notification if callback_url is set
        if getattr(task, "callback_url", None):
            from src.services.push_notifier import send_push_notification
            import asyncio
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
        stmt = (
            select(Agent)
            .options(selectinload(Agent.skills))
            .where(Agent.id == agent_id)
        )
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
