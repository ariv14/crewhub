"""Workflow CRUD service — create, update, clone, convert from crew."""

import uuid as _uuid
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import ForbiddenError, NotFoundError
from src.models.agent import Agent
from src.models.skill import AgentSkill
from src.models.workflow import Workflow, WorkflowStep
from src.schemas.workflow import WorkflowCreate, WorkflowUpdate


class WorkflowService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _step_load_options(self):
        return [
            selectinload(Workflow.steps)
            .selectinload(WorkflowStep.agent)
            .selectinload(Agent.skills),
            selectinload(Workflow.steps)
            .selectinload(WorkflowStep.agent)
            .selectinload(Agent.owner),
            selectinload(Workflow.steps).selectinload(WorkflowStep.skill),
        ]

    async def _get_workflow_or_404(self, workflow_id: UUID) -> Workflow:
        result = await self.db.execute(
            select(Workflow)
            .where(Workflow.id == workflow_id)
            .options(*self._step_load_options())
        )
        wf = result.scalar_one_or_none()
        if not wf:
            raise NotFoundError("Workflow not found")
        return wf

    def _check_ownership(self, wf: Workflow, owner_id: UUID) -> None:
        if wf.owner_id != owner_id:
            raise ForbiddenError("You do not own this workflow")

    async def _validate_step_refs(self, steps: list) -> None:
        if not steps:
            return
        agent_ids = {s.agent_id for s in steps}
        skill_ids = {s.skill_id for s in steps}

        result = await self.db.execute(
            select(Agent.id).where(Agent.id.in_(agent_ids))
        )
        found = {row[0] for row in result.all()}
        missing = agent_ids - found
        if missing:
            raise NotFoundError(f"Agent(s) not found: {missing}")

        result = await self.db.execute(
            select(AgentSkill.id).where(AgentSkill.id.in_(skill_ids))
        )
        found = {row[0] for row in result.all()}
        missing = skill_ids - found
        if missing:
            raise NotFoundError(f"Skill(s) not found: {missing}")

    def _build_steps(self, workflow_id: UUID, steps: list) -> list[WorkflowStep]:
        return [
            WorkflowStep(
                id=_uuid.uuid4(),
                workflow_id=workflow_id,
                agent_id=s.agent_id,
                skill_id=s.skill_id,
                step_group=s.step_group,
                position=s.position,
                input_mode=s.input_mode,
                input_template=s.input_template,
                label=s.label,
            )
            for s in steps
        ]

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_workflow(self, owner_id: UUID, data: WorkflowCreate) -> Workflow:
        await self._validate_step_refs(data.steps)

        wf = Workflow(
            owner_id=owner_id,
            name=data.name,
            description=data.description,
            icon=data.icon,
            is_public=data.is_public,
            max_total_credits=data.max_total_credits,
            timeout_seconds=data.timeout_seconds,
            step_timeout_seconds=data.step_timeout_seconds,
        )
        self.db.add(wf)
        await self.db.flush()

        for step in self._build_steps(wf.id, data.steps):
            self.db.add(step)

        await self.db.commit()
        return await self._get_workflow_or_404(wf.id)

    async def get_workflow(self, workflow_id: UUID) -> Workflow:
        return await self._get_workflow_or_404(workflow_id)

    async def list_my_workflows(self, owner_id: UUID) -> tuple[list[Workflow], int]:
        count_q = select(func.count()).select_from(Workflow).where(Workflow.owner_id == owner_id)
        total = (await self.db.execute(count_q)).scalar_one()

        q = (
            select(Workflow)
            .where(Workflow.owner_id == owner_id)
            .options(*self._step_load_options())
            .order_by(Workflow.updated_at.desc())
        )
        result = await self.db.execute(q)
        workflows = list(result.scalars().unique().all())
        return workflows, total

    async def list_public_workflows(self) -> tuple[list[Workflow], int]:
        count_q = select(func.count()).select_from(Workflow).where(
            Workflow.is_public == True  # noqa: E712
        )
        total = (await self.db.execute(count_q)).scalar_one()

        q = (
            select(Workflow)
            .where(Workflow.is_public == True)  # noqa: E712
            .options(*self._step_load_options())
            .order_by(Workflow.created_at.desc())
        )
        result = await self.db.execute(q)
        workflows = list(result.scalars().unique().all())
        return workflows, total

    async def update_workflow(
        self, workflow_id: UUID, owner_id: UUID, data: WorkflowUpdate
    ) -> Workflow:
        wf = await self._get_workflow_or_404(workflow_id)
        self._check_ownership(wf, owner_id)

        if data.name is not None:
            wf.name = data.name
        if data.description is not None:
            wf.description = data.description
        if data.icon is not None:
            wf.icon = data.icon
        if data.is_public is not None:
            wf.is_public = data.is_public
        if data.max_total_credits is not None:
            wf.max_total_credits = data.max_total_credits if data.max_total_credits > 0 else None
        if data.timeout_seconds is not None:
            wf.timeout_seconds = data.timeout_seconds
        if data.step_timeout_seconds is not None:
            wf.step_timeout_seconds = data.step_timeout_seconds

        if data.steps is not None:
            await self._validate_step_refs(data.steps)
            for s in wf.steps:
                await self.db.delete(s)
            await self.db.flush()
            for step in self._build_steps(workflow_id, data.steps):
                self.db.add(step)

        await self.db.commit()
        self.db.expire_all()
        return await self._get_workflow_or_404(workflow_id)

    async def delete_workflow(self, workflow_id: UUID, owner_id: UUID) -> None:
        wf = await self._get_workflow_or_404(workflow_id)
        self._check_ownership(wf, owner_id)
        await self.db.delete(wf)
        await self.db.commit()

    # ------------------------------------------------------------------
    # Clone
    # ------------------------------------------------------------------

    async def clone_workflow(self, workflow_id: UUID, owner_id: UUID) -> Workflow:
        source = await self._get_workflow_or_404(workflow_id)
        if not source.is_public and source.owner_id != owner_id:
            raise ForbiddenError("Cannot clone a private workflow you don't own")

        new_wf = Workflow(
            owner_id=owner_id,
            name=f"Copy of {source.name}",
            description=source.description,
            icon=source.icon,
            is_public=False,
            max_total_credits=source.max_total_credits,
            timeout_seconds=source.timeout_seconds,
            step_timeout_seconds=source.step_timeout_seconds,
        )
        self.db.add(new_wf)
        await self.db.flush()

        for s in source.steps:
            self.db.add(WorkflowStep(
                workflow_id=new_wf.id,
                agent_id=s.agent_id,
                skill_id=s.skill_id,
                step_group=s.step_group,
                position=s.position,
                input_mode=s.input_mode,
                input_template=s.input_template,
                label=s.label,
            ))

        await self.db.commit()
        return await self._get_workflow_or_404(new_wf.id)

    # ------------------------------------------------------------------
    # Convert from Crew
    # ------------------------------------------------------------------

    async def convert_from_crew(self, crew_id: UUID, owner_id: UUID) -> Workflow:
        from src.services.crew_service import CrewService
        crew_svc = CrewService(self.db)
        crew = await crew_svc.get_crew(crew_id)

        if not crew.is_public and crew.owner_id != owner_id:
            raise ForbiddenError("Cannot convert a private crew you don't own")

        wf = Workflow(
            owner_id=owner_id,
            name=f"{crew.name} (Workflow)",
            description=crew.description,
            icon=crew.icon,
            is_public=False,
        )
        self.db.add(wf)
        await self.db.flush()

        for m in crew.members:
            self.db.add(WorkflowStep(
                workflow_id=wf.id,
                agent_id=m.agent_id,
                skill_id=m.skill_id,
                step_group=0,
                position=m.position,
                input_mode="chain",
            ))

        await self.db.commit()
        return await self._get_workflow_or_404(wf.id)
