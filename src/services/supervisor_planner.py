# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Supervisor planner — LLM-based workflow planning service."""

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.llm_router import completion
from src.models.agent import Agent
from src.models.supervisor_plan import SupervisorPlan as SupervisorPlanRecord
from src.models.workflow import Workflow, WorkflowStep
from src.schemas.supervisor import (
    ApprovePlanRequest,
    ReplanRequest,
    SupervisorPlan,
    SupervisorPlanRequest,
    SupervisorPlanStep,
)

logger = logging.getLogger(__name__)


class SupervisorPlannerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_plan(
        self, request: SupervisorPlanRequest, user_id: uuid.UUID
    ) -> SupervisorPlan:
        """Generate a workflow plan from a natural language goal."""
        # 1. Clean up expired plans
        await self.db.execute(
            delete(SupervisorPlanRecord).where(
                SupervisorPlanRecord.expires_at < datetime.now(timezone.utc)
            )
        )

        # 2. Fetch active agents with skills
        result = await self.db.execute(
            select(Agent)
            .where(Agent.status == "active")
            .options(selectinload(Agent.skills))
        )
        agents = result.scalars().all()

        if not agents:
            raise ValueError("No active agents available for planning")

        # 3. Build agent registry for prompt
        registry = []
        for agent in agents:
            for skill in agent.skills:
                registry.append(
                    {
                        "agent_id": str(agent.id),
                        "agent_name": agent.name,
                        "skill_id": str(skill.id),
                        "skill_name": skill.name,
                        "skill_key": skill.skill_key,
                        "description": skill.description or "",
                        "category": agent.category or "general",
                        "avg_credits": float(skill.avg_credits or 5),
                        "rating": float(agent.reputation_score or 0),
                    }
                )

        # 4. Build LLM prompt
        system_prompt = """You are a workflow architect for CrewHub, an AI agent marketplace.
Given a user's goal and available agents, produce a workflow plan as JSON.

Rules:
- Choose the best agent/skill for each step based on relevance, rating, and cost
- Use step_group numbers: same group = parallel execution, different groups = sequential
- Set input_mode: "chain" (default, pass previous output), "original" (use user input), or "custom"
- Add clear instructions per step explaining what the agent should do
- Keep total cost within budget if specified
- Return ONLY valid JSON, no markdown or explanation

Output exactly this JSON schema:
{
  "name": "workflow name",
  "description": "what this workflow does",
  "steps": [
    {
      "agent_id": "uuid",
      "skill_id": "uuid",
      "agent_name": "name",
      "skill_name": "name",
      "step_group": 0,
      "input_mode": "chain",
      "instructions": "what this step should do",
      "label": "Step label",
      "confidence": 0.95
    }
  ]
}"""

        user_prompt = (
            f"Goal: {request.goal}\n\n"
            f"Available agents and skills:\n{json.dumps(registry, indent=2)}\n\n"
            f"Budget: {request.max_credits or 'no limit'} credits"
        )

        # 5. Call LLM — completion() returns a str (already extracted)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            raw_text = await completion(
                messages=messages, response_format={"type": "json_object"}
            )
            plan_data = json.loads(raw_text)
        except Exception as e:
            raise ValueError(f"Failed to generate plan: {str(e)}")

        # 6. Validate and enrich plan
        valid_agents = {str(a.id): a for a in agents}
        valid_skills: dict[str, object] = {}
        for a in agents:
            for s in a.skills:
                valid_skills[str(s.id)] = s

        validated_steps: list[SupervisorPlanStep] = []
        total_credits = 0.0
        for step in plan_data.get("steps", []):
            agent_id = step.get("agent_id")
            skill_id = step.get("skill_id")

            if agent_id not in valid_agents or skill_id not in valid_skills:
                continue  # skip invalid agents/skills

            skill = valid_skills[skill_id]
            agent = valid_agents[agent_id]
            est_credits = float(skill.avg_credits or 5)
            total_credits += est_credits

            validated_steps.append(
                SupervisorPlanStep(
                    agent_id=uuid.UUID(agent_id),
                    skill_id=uuid.UUID(skill_id),
                    agent_name=agent.name,
                    skill_name=skill.name,
                    step_group=step.get("step_group", 0),
                    input_mode=step.get("input_mode", "chain"),
                    instructions=step.get("instructions"),
                    label=step.get("label"),
                    confidence=min(max(step.get("confidence", 0.5), 0), 1),
                    estimated_credits=est_credits,
                )
            )

        if not validated_steps:
            raise ValueError("Plan validation failed: no valid steps generated")

        # 7. Store plan ephemerally
        plan_id = str(uuid.uuid4())
        plan_record = SupervisorPlanRecord(
            id=uuid.UUID(plan_id),
            user_id=user_id,
            goal=request.goal,
            plan_data={
                "name": plan_data.get("name", "AI-Planned Workflow"),
                "description": plan_data.get("description", ""),
                "steps": [s.model_dump(mode="json") for s in validated_steps],
                "total_estimated_credits": total_credits,
            },
            llm_provider=request.llm_provider or "groq",
            status="draft",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        self.db.add(plan_record)
        await self.db.flush()

        return SupervisorPlan(
            name=plan_data.get("name", "AI-Planned Workflow"),
            description=plan_data.get("description", ""),
            steps=validated_steps,
            total_estimated_credits=total_credits,
            llm_provider_used=request.llm_provider or "groq",
            plan_id=plan_id,
        )

    async def replan(
        self, request: ReplanRequest, user_id: uuid.UUID
    ) -> SupervisorPlan:
        """Regenerate plan with user feedback."""
        # Fetch previous plan
        result = await self.db.execute(
            select(SupervisorPlanRecord).where(
                SupervisorPlanRecord.id == uuid.UUID(request.previous_plan_id),
                SupervisorPlanRecord.user_id == user_id,
            )
        )
        prev_plan = result.scalar_one_or_none()
        if not prev_plan:
            raise ValueError("Previous plan not found or expired")

        # Generate new plan with feedback appended to goal
        new_request = SupervisorPlanRequest(
            goal=f"{request.goal}\n\nFeedback on previous plan: {request.feedback}",
            llm_provider=prev_plan.llm_provider,
        )
        return await self.generate_plan(new_request, user_id)

    async def approve_plan(
        self, request: ApprovePlanRequest, user_id: uuid.UUID
    ) -> Workflow:
        """Convert an approved plan into a saved Workflow."""
        # Fetch plan
        result = await self.db.execute(
            select(SupervisorPlanRecord).where(
                SupervisorPlanRecord.id == uuid.UUID(request.plan_id),
                SupervisorPlanRecord.user_id == user_id,
                SupervisorPlanRecord.status == "draft",
            )
        )
        plan_record = result.scalar_one_or_none()
        if not plan_record:
            raise ValueError("Plan not found, expired, or already approved")

        plan_data = plan_record.plan_data

        # Create workflow
        workflow = Workflow(
            owner_id=user_id,
            name=request.workflow_name or plan_data["name"],
            description=plan_data.get("description", ""),
            pattern_type="supervisor",
            supervisor_config={
                "goal": plan_record.goal,
                "plan_status": "approved",
                "llm_provider": plan_record.llm_provider,
            },
        )
        self.db.add(workflow)
        await self.db.flush()

        # Create steps
        for i, step_data in enumerate(plan_data.get("steps", [])):
            step = WorkflowStep(
                workflow_id=workflow.id,
                agent_id=uuid.UUID(step_data["agent_id"]),
                skill_id=uuid.UUID(step_data["skill_id"]),
                step_group=step_data.get("step_group", 0),
                position=i,
                input_mode=step_data.get("input_mode", "chain"),
                instructions=step_data.get("instructions"),
                label=step_data.get("label"),
            )
            self.db.add(step)

        # Mark plan as approved
        plan_record.status = "approved"
        await self.db.flush()

        return workflow
