"""Service layer for AgentCrew CRUD and execution."""

import uuid as _uuid
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import ForbiddenError, NotFoundError
from src.models.agent import Agent
from src.models.crew import AgentCrew, AgentCrewMember
from src.models.skill import AgentSkill
from src.models.user import User
from src.schemas.crew import (
    CrewCreate,
    CrewRunRequest,
    CrewRunResponse,
    CrewUpdate,
)
from src.schemas.task import TaskCreate as TaskCreateSchema, TaskMessage, MessagePart


class CrewService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_crew_or_404(self, crew_id: UUID) -> AgentCrew:
        result = await self.db.execute(
            select(AgentCrew)
            .where(AgentCrew.id == crew_id)
            .options(
                selectinload(AgentCrew.members)
                .selectinload(AgentCrewMember.agent)
                .selectinload(Agent.skills),
                selectinload(AgentCrew.members)
                .selectinload(AgentCrewMember.agent)
                .selectinload(Agent.owner),
                selectinload(AgentCrew.members).selectinload(AgentCrewMember.skill),
            )
        )
        crew = result.scalar_one_or_none()
        if not crew:
            raise NotFoundError("Crew not found")
        return crew

    def _check_ownership(self, crew: AgentCrew, owner_id: UUID) -> None:
        if crew.owner_id != owner_id:
            raise ForbiddenError("You do not own this crew")

    async def _validate_member_refs(self, members: list) -> None:
        """Validate that all agent_id and skill_id references exist."""
        if not members:
            return
        agent_ids = {m.agent_id for m in members}
        skill_ids = {m.skill_id for m in members}

        result = await self.db.execute(
            select(Agent.id).where(Agent.id.in_(agent_ids))
        )
        found_agents = {row[0] for row in result.all()}
        missing = agent_ids - found_agents
        if missing:
            raise NotFoundError(f"Agent(s) not found: {missing}")

        result = await self.db.execute(
            select(AgentSkill.id).where(AgentSkill.id.in_(skill_ids))
        )
        found_skills = {row[0] for row in result.all()}
        missing = skill_ids - found_skills
        if missing:
            raise NotFoundError(f"Skill(s) not found: {missing}")

    def _build_members(self, crew_id: UUID, members: list) -> list[AgentCrewMember]:
        return [
            AgentCrewMember(
                id=_uuid.uuid4(),
                crew_id=crew_id,
                agent_id=m.agent_id,
                skill_id=m.skill_id,
                position=m.position,
            )
            for m in members
        ]

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_crew(self, owner_id: UUID, data: CrewCreate) -> AgentCrew:
        await self._validate_member_refs(data.members)

        crew = AgentCrew(
            owner_id=owner_id,
            name=data.name,
            description=data.description,
            icon=data.icon,
            is_public=data.is_public,
        )
        self.db.add(crew)
        await self.db.flush()

        for member in self._build_members(crew.id, data.members):
            self.db.add(member)

        await self.db.commit()
        # Re-fetch with all nested relationships eagerly loaded
        return await self._get_crew_or_404(crew.id)

    async def get_crew(self, crew_id: UUID) -> AgentCrew:
        return await self._get_crew_or_404(crew_id)

    async def list_my_crews(self, owner_id: UUID) -> tuple[list[AgentCrew], int]:
        count_q = select(func.count()).select_from(AgentCrew).where(AgentCrew.owner_id == owner_id)
        total = (await self.db.execute(count_q)).scalar_one()

        q = (
            select(AgentCrew)
            .where(AgentCrew.owner_id == owner_id)
            .options(
                selectinload(AgentCrew.members)
                .selectinload(AgentCrewMember.agent)
                .selectinload(Agent.skills),
                selectinload(AgentCrew.members)
                .selectinload(AgentCrewMember.agent)
                .selectinload(Agent.owner),
                selectinload(AgentCrew.members).selectinload(AgentCrewMember.skill),
            )
            .order_by(AgentCrew.updated_at.desc())
        )
        result = await self.db.execute(q)
        crews = list(result.scalars().unique().all())
        return crews, total

    async def list_public_crews(self) -> tuple[list[AgentCrew], int]:
        count_q = select(func.count()).select_from(AgentCrew).where(AgentCrew.is_public == True)  # noqa: E712
        total = (await self.db.execute(count_q)).scalar_one()

        q = (
            select(AgentCrew)
            .where(AgentCrew.is_public == True)  # noqa: E712
            .options(
                selectinload(AgentCrew.members)
                .selectinload(AgentCrewMember.agent)
                .selectinload(Agent.skills),
                selectinload(AgentCrew.members)
                .selectinload(AgentCrewMember.agent)
                .selectinload(Agent.owner),
                selectinload(AgentCrew.members).selectinload(AgentCrewMember.skill),
            )
            .order_by(AgentCrew.created_at.desc())
        )
        result = await self.db.execute(q)
        crews = list(result.scalars().unique().all())
        return crews, total

    async def update_crew(self, crew_id: UUID, owner_id: UUID, data: CrewUpdate) -> AgentCrew:
        crew = await self._get_crew_or_404(crew_id)
        self._check_ownership(crew, owner_id)

        if data.name is not None:
            crew.name = data.name
        if data.description is not None:
            crew.description = data.description
        if data.icon is not None:
            crew.icon = data.icon
        if data.is_public is not None:
            crew.is_public = data.is_public

        if data.members is not None:
            await self._validate_member_refs(data.members)
            # Evict cached members from session identity map
            for m in crew.members:
                await self.db.delete(m)
            await self.db.flush()
            # Insert new members
            for member in self._build_members(crew_id, data.members):
                self.db.add(member)

        await self.db.commit()
        # Expire all cached state so re-fetch gets fresh data
        self.db.expire_all()
        # Re-fetch with all nested relationships eagerly loaded
        return await self._get_crew_or_404(crew_id)

    async def delete_crew(self, crew_id: UUID, owner_id: UUID) -> None:
        crew = await self._get_crew_or_404(crew_id)
        self._check_ownership(crew, owner_id)
        await self.db.delete(crew)
        await self.db.commit()

    # ------------------------------------------------------------------
    # Clone
    # ------------------------------------------------------------------

    async def clone_crew(self, crew_id: UUID, owner_id: UUID) -> AgentCrew:
        source = await self._get_crew_or_404(crew_id)
        # Allow cloning public crews or own crews
        if not source.is_public and source.owner_id != owner_id:
            raise ForbiddenError("Cannot clone a private crew you don't own")

        new_crew = AgentCrew(
            owner_id=owner_id,
            name=f"Copy of {source.name}",
            description=source.description,
            icon=source.icon,
            is_public=False,
        )
        self.db.add(new_crew)
        await self.db.flush()

        for m in source.members:
            self.db.add(AgentCrewMember(
                crew_id=new_crew.id,
                agent_id=m.agent_id,
                skill_id=m.skill_id,
                position=m.position,
            ))

        await self.db.commit()
        # Re-fetch with all nested relationships eagerly loaded
        return await self._get_crew_or_404(new_crew.id)

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    async def run_crew(
        self, crew_id: UUID, owner_id: UUID, data: CrewRunRequest
    ) -> CrewRunResponse:
        from src.services.task_broker import TaskBrokerService

        crew = await self._get_crew_or_404(crew_id)
        # Allow running own crews or public crews
        if not crew.is_public and crew.owner_id != owner_id:
            raise ForbiddenError("Cannot run a private crew you don't own")

        broker = TaskBrokerService(self.db)
        task_ids: list[_uuid.UUID] = []
        member_task_map: dict[str, str] = {}

        message = TaskMessage(
            role="user",
            parts=[MessagePart(type="text", content=data.message)],
        )

        for member in crew.members:
            task_data = TaskCreateSchema(
                provider_agent_id=member.agent_id,
                skill_id=str(member.skill_id),
                messages=[message],
                confirmed=True,
            )
            task = await broker.create_task(data=task_data, user_id=owner_id)
            task_ids.append(task.id)
            member_task_map[str(member.agent_id)] = str(task.id)

        return CrewRunResponse(
            crew_id=crew_id,
            task_ids=task_ids,
            member_task_map=member_task_map,
        )
