# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Agent registry service -- register, update, list, and manage agents."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.embeddings import EmbeddingService
from src.core.encryption import decrypt_value
from src.core.exceptions import ForbiddenError, NotFoundError
from src.models.agent import Agent, AgentStatus
from src.models.skill import AgentSkill
from src.models.user import User
from src.schemas.agent import AgentCreate, AgentUpdate


class RegistryService:
    """Handles agent registration, updates, listing, and agent-card generation."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _resolve_embeddings(
        self, owner_id: UUID, agent_embedding_config: dict | None = None
    ) -> EmbeddingService:
        """Resolve embedding service: agent config → user keys → platform config."""
        # Get owner's LLM keys
        owner_keys: dict[str, str] = {}
        user = await self.db.get(User, owner_id)
        if user and user.llm_api_keys:
            for provider, encrypted in user.llm_api_keys.items():
                decrypted = decrypt_value(encrypted)
                if decrypted:
                    owner_keys[provider] = decrypted

        return EmbeddingService.for_agent(
            agent_embedding_config=agent_embedding_config,
            owner_llm_keys=owner_keys,
        )

    # ------------------------------------------------------------------
    # Register
    # ------------------------------------------------------------------

    async def register_agent(self, owner_id: UUID, data: AgentCreate) -> Agent:
        """Create a new agent record together with its skills.

        Steps:
            1. Check for duplicate endpoint.
            2. Persist the Agent row.
            3. Persist each AgentSkill row.
            4. Generate embeddings for every skill and store them.
            5. Return the agent with skills loaded.
        """
        # Reject duplicate endpoints (check active/inactive agents)
        if data.endpoint:
            existing = await self.db.execute(
                select(Agent.id).where(
                    Agent.endpoint == data.endpoint,
                    Agent.status.in_([AgentStatus.ACTIVE, AgentStatus.INACTIVE]),
                )
            )
            if existing.scalar_one_or_none():
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=409,
                    detail=f"An agent with endpoint '{data.endpoint}' is already registered.",
                )

        embedding_cfg = data.embedding_config.model_dump() if data.embedding_config else {}

        # Generate DID keypair for the agent
        from src.core.did import encrypt_private_key, generate_did_keypair
        public_key, private_key = generate_did_keypair()

        agent = Agent(
            owner_id=owner_id,
            name=data.name,
            description=data.description,
            version=data.version,
            endpoint=data.endpoint,
            capabilities=data.capabilities,
            security_schemes=data.security_schemes,
            category=data.category,
            tags=data.tags,
            pricing=data.pricing.model_dump(),
            license_type=data.pricing.license_type.value,
            sla=data.sla.model_dump() if data.sla else {},
            embedding_config=embedding_cfg,
            accepted_payment_methods=data.accepted_payment_methods,
            mcp_server_url=getattr(data, "mcp_server_url", None),
            avatar_url=getattr(data, "avatar_url", None),
            conversation_starters=getattr(data, "conversation_starters", []),
            test_cases=getattr(data, "test_cases", []),
            did_public_key=public_key,
            did_private_key_encrypted=encrypt_private_key(private_key),
            metadata_={},
            status=AgentStatus.ACTIVE,
        )
        self.db.add(agent)
        await self.db.flush()

        # Create skills and collect texts for batch embedding
        skills: list[AgentSkill] = []
        embedding_texts: list[str] = []
        for skill_data in data.skills:
            skill = AgentSkill(
                agent_id=agent.id,
                skill_key=skill_data.skill_key,
                name=skill_data.name,
                description=skill_data.description,
                input_modes=skill_data.input_modes,
                output_modes=skill_data.output_modes,
                examples=[ex.model_dump() for ex in skill_data.examples],
                avg_credits=skill_data.avg_credits,
                avg_latency_ms=skill_data.avg_latency_ms,
            )
            self.db.add(skill)
            skills.append(skill)
            embedding_texts.append(f"{skill_data.name}: {skill_data.description}")

        await self.db.flush()

        # Generate and store embeddings (agent → user → platform resolution)
        if embedding_texts:
            embed_svc = await self._resolve_embeddings(owner_id, embedding_cfg or None)
            embeddings = await embed_svc.generate_batch(embedding_texts)
            for skill, emb in zip(skills, embeddings):
                skill.embedding = emb
            await self.db.flush()

        await self.db.commit()
        # Re-fetch with skills eagerly loaded.
        # populate_existing=True forces SQLAlchemy to overwrite the identity-map
        # cache so skills are actually loaded even with expire_on_commit=False.
        result = await self.db.execute(
            select(Agent)
            .options(selectinload(Agent.skills))
            .where(Agent.id == agent.id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one()

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    async def list_agents(
        self,
        page: int = 1,
        per_page: int = 20,
        category: str | None = None,
        status: str = "active",
        owner_id: str | None = None,
    ) -> tuple[list[Agent], int]:
        """Return a paginated list of agents with optional filters."""
        query = select(Agent).options(selectinload(Agent.skills))

        if status:
            # Support "active" returning both active and unavailable (public-facing)
            if status == "active":
                query = query.where(
                    Agent.status.in_([AgentStatus.ACTIVE, AgentStatus.UNAVAILABLE])
                )
            else:
                query = query.where(Agent.status == status)
        if category:
            query = query.where(Agent.category == category)
        if owner_id:
            query = query.where(Agent.owner_id == owner_id)

        # Total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        # Paginate
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page).order_by(Agent.created_at.desc())
        result = await self.db.execute(query)
        agents = list(result.scalars().unique().all())

        return agents, total

    # ------------------------------------------------------------------
    # Get
    # ------------------------------------------------------------------

    async def get_agent(self, agent_id: UUID) -> Agent:
        """Get a single agent by ID with skills eagerly loaded."""
        query = (
            select(Agent)
            .options(selectinload(Agent.skills))
            .where(Agent.id == agent_id)
        )
        result = await self.db.execute(query)
        agent = result.scalars().first()
        if not agent:
            raise NotFoundError(detail=f"Agent {agent_id} not found")
        return agent

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update_agent(
        self, agent_id: UUID, owner_id: UUID, data: AgentUpdate
    ) -> Agent:
        """Update agent fields after verifying ownership."""
        agent = await self.get_agent(agent_id)
        if agent.owner_id != owner_id:
            raise ForbiddenError(detail="You do not own this agent")

        update_data = data.model_dump(exclude_unset=True)

        # Handle nested pydantic models
        if "pricing" in update_data and update_data["pricing"] is not None:
            update_data["pricing"] = data.pricing.model_dump()
        if "sla" in update_data and update_data["sla"] is not None:
            update_data["sla"] = data.sla.model_dump()
        if "embedding_config" in update_data and update_data["embedding_config"] is not None:
            update_data["embedding_config"] = data.embedding_config.model_dump()

        # Handle skills separately -- rebuild skill rows and embeddings
        new_skills_data = update_data.pop("skills", None)
        for field, value in update_data.items():
            setattr(agent, field, value)

        if new_skills_data is not None:
            # Remove existing skills
            for existing in list(agent.skills):
                await self.db.delete(existing)
            await self.db.flush()

            skills: list[AgentSkill] = []
            embedding_texts: list[str] = []
            for skill_data in data.skills:
                skill = AgentSkill(
                    agent_id=agent.id,
                    skill_key=skill_data.skill_key,
                    name=skill_data.name,
                    description=skill_data.description,
                    input_modes=skill_data.input_modes,
                    output_modes=skill_data.output_modes,
                    examples=[ex.model_dump() for ex in skill_data.examples],
                    avg_credits=skill_data.avg_credits,
                    avg_latency_ms=skill_data.avg_latency_ms,
                )
                self.db.add(skill)
                skills.append(skill)
                embedding_texts.append(f"{skill_data.name}: {skill_data.description}")

            await self.db.flush()

            if embedding_texts:
                embed_svc = await self._resolve_embeddings(
                    owner_id, agent.embedding_config or None
                )
                embeddings = await embed_svc.generate_batch(embedding_texts)
                for skill, emb in zip(skills, embeddings):
                    skill.embedding = emb
                await self.db.flush()

        await self.db.commit()
        result = await self.db.execute(
            select(Agent)
            .options(selectinload(Agent.skills))
            .where(Agent.id == agent.id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one()

    # ------------------------------------------------------------------
    # Deactivate
    # ------------------------------------------------------------------

    async def deactivate_agent(self, agent_id: UUID, owner_id: UUID) -> None:
        """Set agent status to inactive after verifying ownership."""
        agent = await self.get_agent(agent_id)
        if agent.owner_id != owner_id:
            raise ForbiddenError(detail="You do not own this agent")

        agent.status = AgentStatus.INACTIVE
        await self.db.commit()

    async def hard_delete_agent(self, agent_id: UUID, owner_id: UUID) -> None:
        """Permanently delete an agent and its skills from the database."""
        agent = await self.get_agent(agent_id)
        if agent.owner_id != owner_id:
            raise ForbiddenError(detail="You do not own this agent")

        await self.db.delete(agent)
        await self.db.commit()

    # ------------------------------------------------------------------
    # Agent Card
    # ------------------------------------------------------------------

    async def get_agent_card(self, agent_id: UUID) -> dict:
        """Generate an A2A-spec compliant agent card JSON."""
        agent = await self.get_agent(agent_id)

        # Collect default input/output modes from all skills
        all_input_modes: set[str] = set()
        all_output_modes: set[str] = set()
        skill_cards: list[dict] = []
        for skill in agent.skills:
            all_input_modes.update(skill.input_modes or [])
            all_output_modes.update(skill.output_modes or [])
            skill_cards.append(
                {
                    "id": skill.skill_key,
                    "name": skill.name,
                    "description": skill.description,
                    "inputModes": skill.input_modes or [],
                    "outputModes": skill.output_modes or [],
                    "examples": skill.examples or [],
                }
            )

        return {
            "name": agent.name,
            "description": agent.description or "",
            "url": agent.endpoint,
            "version": agent.version,
            "capabilities": agent.capabilities or {},
            "skills": skill_cards,
            "securitySchemes": agent.security_schemes if isinstance(agent.security_schemes, list) else [],
            "defaultInputModes": sorted(all_input_modes),
            "defaultOutputModes": sorted(all_output_modes),
        }

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    async def request_verification(self, agent_id: UUID, owner_id: UUID) -> dict:
        """Placeholder -- submit a verification request for the agent."""
        agent = await self.get_agent(agent_id)
        if agent.owner_id != owner_id:
            raise ForbiddenError(detail="You do not own this agent")

        return {
            "agent_id": str(agent.id),
            "current_level": agent.verification_level,
            "status": "pending",
            "message": "Verification request submitted. Review typically takes 24-48 hours.",
        }
