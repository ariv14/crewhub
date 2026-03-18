# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Supervisor workflow planning API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.auth import resolve_db_user_id
from src.core.rate_limiter import rate_limit_dependency
from src.database import get_db
from src.models.agent import Agent
from src.models.workflow import Workflow, WorkflowStep
from src.schemas.supervisor import (
    ApprovePlanRequest,
    ReplanRequest,
    SupervisorPlan,
    SupervisorPlanRequest,
)
from src.schemas.workflow import WorkflowResponse
from src.services.supervisor_planner import SupervisorPlannerService

router = APIRouter(prefix="/workflows/supervisor", tags=["supervisor"])


@router.post("/plan", response_model=SupervisorPlan, dependencies=[Depends(rate_limit_dependency)])
async def generate_plan(
    request: SupervisorPlanRequest,
    owner_id: UUID = Depends(resolve_db_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate a workflow plan from a natural language goal."""
    service = SupervisorPlannerService(db)
    plan = await service.generate_plan(request, owner_id)
    await db.commit()
    return plan


@router.post("/replan", response_model=SupervisorPlan, dependencies=[Depends(rate_limit_dependency)])
async def replan(
    request: ReplanRequest,
    owner_id: UUID = Depends(resolve_db_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Regenerate plan with user feedback."""
    service = SupervisorPlannerService(db)
    plan = await service.replan(request, owner_id)
    await db.commit()
    return plan


@router.post("/approve", response_model=WorkflowResponse, dependencies=[Depends(rate_limit_dependency)])
async def approve_plan(
    request: ApprovePlanRequest,
    owner_id: UUID = Depends(resolve_db_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Convert an approved plan into a saved Workflow."""
    service = SupervisorPlannerService(db)
    workflow = await service.approve_plan(request, owner_id)
    await db.commit()
    # Reload with relationships for response
    result = await db.execute(
        select(Workflow)
        .where(Workflow.id == workflow.id)
        .options(
            selectinload(Workflow.steps)
            .selectinload(WorkflowStep.agent)
            .selectinload(Agent.skills),
            selectinload(Workflow.steps).selectinload(WorkflowStep.skill),
        )
    )
    workflow = result.scalar_one()
    return workflow
