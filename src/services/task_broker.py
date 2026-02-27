"""Task broker service -- create, manage, and rate tasks between agents."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import ForbiddenError, NotFoundError
from src.models.agent import Agent, AgentStatus
from src.models.skill import AgentSkill
from src.models.task import Task, TaskStatus
from src.schemas.task import TaskCreate, TaskMessage, TaskRating
from src.services.credit_ledger import CreditLedgerService


class TaskBrokerService:
    """Orchestrates task lifecycle between client and provider agents."""

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

        # 3. Quote credits from pricing tiers or legacy pricing
        credits_quoted = Decimal(str(
            self._resolve_credits(provider, data.max_credits, skill.avg_credits, data.tier)
        ))

        # 4. Reserve credits
        if credits_quoted > 0:
            await self.credit_ledger.reserve_credits(
                owner_id=user_id,
                amount=float(credits_quoted),
                task_id=None,  # task not created yet; updated after creation
            )

        # 5. Create task
        task = Task(
            client_agent_id=client_agent_id,
            provider_agent_id=provider.id,
            skill_id=skill.id,
            status=TaskStatus.SUBMITTED,
            messages=[m.model_dump() for m in data.messages],
            artifacts=[],
            credits_quoted=credits_quoted,
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

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
            owns_client = task.client_agent and task.client_agent.owner_id == user_id
            owns_provider = task.provider_agent and task.provider_agent.owner_id == user_id
            if not owns_client and not owns_provider:
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
            # Tasks where the user owns either the client or provider agent
            stmt = stmt.outerjoin(
                Agent,
                (Agent.id == Task.client_agent_id) | (Agent.id == Task.provider_agent_id),
            ).where(Agent.owner_id == user_id)
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
        task.status = status

        if artifacts:
            task.artifacts = artifacts

        now = datetime.now(timezone.utc)

        if status == TaskStatus.COMPLETED:
            task.completed_at = now
            # Calculate latency
            if task.created_at:
                delta = now - task.created_at
                task.latency_ms = int(delta.total_seconds() * 1000)

            # Charge credits
            quoted = float(task.credits_quoted or 0)
            if quoted > 0 and task.client_agent and task.provider_agent:
                client_agent = task.client_agent
                provider_agent = task.provider_agent
                txn = await self.credit_ledger.charge_credits(
                    client_owner_id=client_agent.owner_id,
                    provider_owner_id=provider_agent.owner_id,
                    amount=quoted,
                    task_id=task.id,
                )
                task.credits_charged = Decimal(str(quoted))

            # Update provider stats
            if task.provider_agent:
                await self._update_provider_stats(task.provider_agent)

        elif status == TaskStatus.FAILED:
            # Release reserved credits
            quoted = float(task.credits_quoted or 0)
            if quoted > 0 and task.client_agent:
                await self.credit_ledger.release_credits(
                    owner_id=task.client_agent.owner_id,
                    amount=quoted,
                    task_id=task.id,
                )

        await self.db.commit()
        await self.db.refresh(task)
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
        terminal = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED}
        if task.status in terminal:
            raise ForbiddenError(
                detail=f"Cannot cancel task in '{task.status.value}' state"
            )

        task.status = TaskStatus.CANCELED

        quoted = float(task.credits_quoted or 0)
        if quoted > 0 and task.client_agent:
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
