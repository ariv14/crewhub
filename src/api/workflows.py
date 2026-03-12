"""Workflow API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import resolve_db_user_id
from src.database import get_db
from src.schemas.workflow import (
    WorkflowCreate,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowRunListResponse,
    WorkflowRunRequest,
    WorkflowRunResponse,
    WorkflowUpdate,
)
from src.services.workflow_execution import WorkflowExecutionService
from src.services.workflow_service import WorkflowService

router = APIRouter(prefix="/workflows", tags=["workflows"])


# --- Public endpoints (before {id} to avoid path collision) ---

@router.get("/public", response_model=WorkflowListResponse)
async def list_public_workflows(
    db: AsyncSession = Depends(get_db),
) -> WorkflowListResponse:
    service = WorkflowService(db)
    workflows, total = await service.list_public_workflows()
    return WorkflowListResponse(workflows=workflows, total=total)


# --- Authenticated endpoints ---

@router.get("/", response_model=WorkflowListResponse)
async def list_my_workflows(
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(resolve_db_user_id),
) -> WorkflowListResponse:
    service = WorkflowService(db)
    workflows, total = await service.list_my_workflows(owner_id)
    return WorkflowListResponse(workflows=workflows, total=total)


@router.post("/", response_model=WorkflowResponse, status_code=201)
async def create_workflow(
    data: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(resolve_db_user_id),
) -> WorkflowResponse:
    service = WorkflowService(db)
    return await service.create_workflow(owner_id, data)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> WorkflowResponse:
    service = WorkflowService(db)
    return await service.get_workflow(workflow_id)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    data: WorkflowUpdate,
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(resolve_db_user_id),
) -> WorkflowResponse:
    service = WorkflowService(db)
    return await service.update_workflow(workflow_id, owner_id, data)


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(resolve_db_user_id),
) -> None:
    service = WorkflowService(db)
    await service.delete_workflow(workflow_id, owner_id)


@router.post("/{workflow_id}/clone", response_model=WorkflowResponse, status_code=201)
async def clone_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(resolve_db_user_id),
) -> WorkflowResponse:
    service = WorkflowService(db)
    return await service.clone_workflow(workflow_id, owner_id)


@router.post("/{workflow_id}/run", response_model=WorkflowRunResponse)
async def run_workflow(
    workflow_id: UUID,
    data: WorkflowRunRequest,
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(resolve_db_user_id),
) -> WorkflowRunResponse:
    engine = WorkflowExecutionService(db)
    return await engine.execute_workflow(workflow_id, owner_id, data.message)


@router.get("/{workflow_id}/runs", response_model=WorkflowRunListResponse)
async def list_workflow_runs(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(resolve_db_user_id),
) -> WorkflowRunListResponse:
    from sqlalchemy import func, select
    from sqlalchemy.orm import selectinload
    from src.models.workflow import WorkflowRun

    count_q = (
        select(func.count())
        .select_from(WorkflowRun)
        .where(WorkflowRun.workflow_id == workflow_id, WorkflowRun.user_id == owner_id)
    )
    total = (await db.execute(count_q)).scalar_one()

    q = (
        select(WorkflowRun)
        .where(WorkflowRun.workflow_id == workflow_id, WorkflowRun.user_id == owner_id)
        .options(selectinload(WorkflowRun.step_runs))
        .order_by(WorkflowRun.created_at.desc())
        .limit(50)
    )
    result = await db.execute(q)
    runs = list(result.scalars().unique().all())
    return WorkflowRunListResponse(runs=runs, total=total)


# --- Run-level endpoints ---

@router.get("/runs/{run_id}/output")
async def get_workflow_run_output(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get workflow run output in a clean format for external consumption."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from src.models.workflow import WorkflowRun

    result = await db.execute(
        select(WorkflowRun)
        .where(WorkflowRun.id == run_id)
        .options(selectinload(WorkflowRun.step_runs))
    )
    run = result.scalar_one_or_none()
    if not run:
        from src.core.exceptions import NotFoundError
        raise NotFoundError("Workflow run not found")

    snapshot = run.workflow_snapshot or {}
    snapshot_steps = snapshot.get("steps", [])

    def step_label(step_id):
        if step_id:
            sid = str(step_id)
            for s in snapshot_steps:
                if s.get("id") == sid:
                    agent = s.get("agent_name", "")
                    skill = s.get("skill_name", "")
                    return f"{agent} · {skill}" if agent and skill else agent or "Unknown"
        return "Unknown"

    # Build per-step outputs sorted by group then position
    step_outputs = []
    sorted_srs = sorted(run.step_runs, key=lambda sr: (sr.step_group, getattr(sr, 'id', '')))
    for sr in sorted_srs:
        step_outputs.append({
            "step_run_id": str(sr.id),
            "step_group": sr.step_group,
            "label": step_label(sr.step_id),
            "status": sr.status,
            "output_text": sr.output_text,
            "error": sr.error,
            "credits_charged": float(sr.credits_charged) if sr.credits_charged else None,
        })

    # Build combined final output (only completed steps)
    completed_outputs = [
        sr.output_text for sr in sorted_srs
        if sr.status == "completed" and sr.output_text
    ]
    final_output = "\n\n---\n\n".join(completed_outputs) if completed_outputs else None

    return {
        "run_id": str(run.id),
        "workflow_id": str(run.workflow_id),
        "status": run.status,
        "input_message": run.input_message,
        "final_output": final_output,
        "step_outputs": step_outputs,
        "total_credits_charged": float(run.total_credits_charged) if run.total_credits_charged else None,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


@router.get("/runs/{run_id}", response_model=WorkflowRunResponse)
async def get_workflow_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> WorkflowRunResponse:
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from src.models.workflow import WorkflowRun

    result = await db.execute(
        select(WorkflowRun)
        .where(WorkflowRun.id == run_id)
        .options(selectinload(WorkflowRun.step_runs))
    )
    run = result.scalar_one_or_none()
    if not run:
        from src.core.exceptions import NotFoundError
        raise NotFoundError("Workflow run not found")
    return run


@router.post("/runs/{run_id}/cancel", response_model=WorkflowRunResponse)
async def cancel_workflow_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
) -> WorkflowRunResponse:
    engine = WorkflowExecutionService(db)
    return await engine.cancel_run(run_id, user_id)


@router.post(
    "/runs/{run_id}/steps/{step_run_id}/cancel",
    response_model=WorkflowRunResponse,
)
async def cancel_step_run(
    run_id: UUID,
    step_run_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(resolve_db_user_id),
) -> WorkflowRunResponse:
    engine = WorkflowExecutionService(db)
    return await engine.cancel_step_run(run_id, step_run_id, user_id)


# --- Convert from crew ---

@router.post("/from-crew/{crew_id}", response_model=WorkflowResponse, status_code=201)
async def convert_crew_to_workflow(
    crew_id: UUID,
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(resolve_db_user_id),
) -> WorkflowResponse:
    service = WorkflowService(db)
    return await service.convert_from_crew(crew_id, owner_id)
