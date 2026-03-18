# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Supervisor workflow planning API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.core.auth import get_current_user
from src.services.supervisor_planner import SupervisorPlannerService
from src.schemas.supervisor import (
    SupervisorPlanRequest, SupervisorPlan,
    ReplanRequest, ApprovePlanRequest,
)
from src.schemas.workflow import WorkflowResponse

router = APIRouter(prefix="/workflows/supervisor", tags=["supervisor"])


@router.post("/plan", response_model=SupervisorPlan)
async def generate_plan(
    request: SupervisorPlanRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a workflow plan from a natural language goal."""
    from src.core.auth import resolve_db_user_id
    db_user_id = await resolve_db_user_id(user_id, db)
    service = SupervisorPlannerService(db)
    plan = await service.generate_plan(request, db_user_id)
    await db.commit()
    return plan


@router.post("/replan", response_model=SupervisorPlan)
async def replan(
    request: ReplanRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Regenerate plan with user feedback."""
    from src.core.auth import resolve_db_user_id
    db_user_id = await resolve_db_user_id(user_id, db)
    service = SupervisorPlannerService(db)
    plan = await service.replan(request, db_user_id)
    await db.commit()
    return plan


@router.post("/approve", response_model=WorkflowResponse)
async def approve_plan(
    request: ApprovePlanRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert an approved plan into a saved Workflow."""
    from src.core.auth import resolve_db_user_id
    db_user_id = await resolve_db_user_id(user_id, db)
    service = SupervisorPlannerService(db)
    workflow = await service.approve_plan(request, db_user_id)
    await db.commit()
    # Reload with relationships for response
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from src.models.workflow import Workflow, WorkflowStep
    from src.models.agent import Agent
    result = await db.execute(
        select(Workflow)
        .where(Workflow.id == workflow.id)
        .options(
            selectinload(Workflow.steps).selectinload(WorkflowStep.agent).selectinload(Agent.skills),
            selectinload(Workflow.steps).selectinload(WorkflowStep.skill),
        )
    )
    workflow = result.scalar_one()
    return workflow
