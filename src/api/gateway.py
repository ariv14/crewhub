# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Gateway-facing API endpoints — server-to-server, authenticated via X-Gateway-Key.

These endpoints are called by the external Multi-Channel Gateway service to:
- Charge credits for channel messages
- Retrieve connection credentials (decrypted)
- Report connection heartbeats
- Log individual messages
- Receive task completion callbacks
"""

import hmac
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.encryption import decrypt_value
from src.database import get_db
from src.models.account import Account
from src.models.channel import ChannelConnection, ChannelContactBlock, ChannelMessage
from src.schemas.channel import (
    GatewayChargeRequest,
    GatewayChargeResponse,
    GatewayConnectionResponse,
    GatewayCreateTaskRequest,
    GatewayCreateWorkflowRunRequest,
    GatewayCreateWorkflowRunResponse,
    GatewayHeartbeatRequest,
    GatewayLogMessageRequest,
    GatewayPendingWorkflowDeliveriesResponse,
    GatewayPendingWorkflowDelivery,
    GatewayWorkflowRunStatusResponse,
)
from src.services.credit_ledger import CreditLedgerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gateway", tags=["gateway"])


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------


async def require_gateway_key(
    x_gateway_key: str = Header(..., alias="X-Gateway-Key"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Validate the shared gateway service key.

    - 503 if gateway_service_key is not configured (empty).
    - 401 if the provided key doesn't match (audit-logged).
    """
    if not settings.gateway_service_key:
        raise HTTPException(
            status_code=503,
            detail="Gateway authentication not configured on this server.",
        )
    if not hmac.compare_digest(x_gateway_key, settings.gateway_service_key):
        # Audit log auth failure (SOC 2 CC7.2)
        try:
            await _audit_gateway(db, "auth_failure", request=request)
            await db.commit()
        except Exception:
            pass
        logger.warning("Gateway auth failure from %s", request.client.host if request and request.client else "unknown")
        raise HTTPException(status_code=401, detail="Invalid gateway key.")


# ---------------------------------------------------------------------------
# Rate limiting (backend-side fallback — catches bypasses of CF Worker in-memory limits)
# ---------------------------------------------------------------------------

from src.core.rate_limiter import rate_limit_by_ip


# ---------------------------------------------------------------------------
# Audit logging for gateway security events
# ---------------------------------------------------------------------------

async def _audit_gateway(db, action: str, request: Request = None, **kwargs):
    """Log a gateway security event."""
    from src.core.audit import audit_log
    await audit_log(
        db, action=f"gateway.{action}",
        actor_user_id="gateway-service",
        target_type="gateway",
        request=request,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/charge", response_model=GatewayChargeResponse, dependencies=[Depends(rate_limit_by_ip)])
async def charge_for_message(
    req: GatewayChargeRequest,
    _: None = Depends(require_gateway_key),
    db: AsyncSession = Depends(get_db),
) -> GatewayChargeResponse:
    """Deduct credits from the connection owner's account for a channel message.

    Enforces the daily credit limit for this connection (if set). Uses
    SELECT FOR UPDATE on the account row for atomicity.
    """
    # Fetch the connection to get the owner
    connection = await db.get(ChannelConnection, req.connection_id)
    if not connection:
        return GatewayChargeResponse(success=False, error="Connection not found.")

    owner_id: UUID = connection.owner_id

    # Determine effective daily limit (request overrides connection setting)
    daily_limit = req.daily_credit_limit if req.daily_credit_limit is not None else connection.daily_credit_limit

    # Compute today's usage for this connection
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    usage_stmt = select(
        func.coalesce(func.sum(ChannelMessage.credits_charged), 0)
    ).where(
        ChannelMessage.connection_id == req.connection_id,
        ChannelMessage.created_at >= today_start,
    )
    today_usage = float((await db.execute(usage_stmt)).scalar_one())

    # Check daily limit
    if daily_limit and (today_usage + req.credits) > daily_limit:
        # Get remaining balance for response
        ledger = CreditLedgerService(db)
        balance_info = await ledger.get_balance(owner_id)
        return GatewayChargeResponse(
            success=False,
            remaining_balance=balance_info["available"],
            today_usage=today_usage,
            error=f"Daily credit limit of {daily_limit} would be exceeded (used today: {today_usage:.2f}).",
        )

    # Lock account row for atomic debit
    account_stmt = (
        select(Account)
        .where(Account.owner_id == owner_id)
        .with_for_update()
    )
    result = await db.execute(account_stmt)
    account = result.scalars().first()

    if not account:
        # Create account (gives signup bonus, then proceed)
        ledger = CreditLedgerService(db)
        account = await ledger.get_or_create_account(owner_id)
        result = await db.execute(
            select(Account).where(Account.owner_id == owner_id).with_for_update()
        )
        account = result.scalars().first()

    from decimal import Decimal

    dec_credits = Decimal(str(req.credits))
    available = account.balance - account.reserved

    if available < dec_credits:
        return GatewayChargeResponse(
            success=False,
            remaining_balance=float(available),
            today_usage=today_usage,
            error=f"Insufficient credits (available: {float(available):.2f}, required: {req.credits}).",
        )

    account.balance -= dec_credits
    await db.commit()

    # Refresh for updated balance
    await db.refresh(account)
    remaining = float(account.balance - account.reserved)
    new_today_usage = today_usage + req.credits

    logger.info(
        "Gateway charge: connection=%s owner=%s credits=%.4f today_usage=%.4f",
        req.connection_id,
        owner_id,
        req.credits,
        new_today_usage,
    )

    # SOC 2 CC7.2: audit log for credit charges (non-blocking)
    try:
        await _audit_gateway(
            db, "charge",
            target_id=str(req.connection_id),
            new_value={"credits": req.credits, "owner": str(owner_id), "remaining": round(remaining, 2)},
        )
        await db.commit()
    except Exception:
        logger.warning("Audit log for charge failed (non-blocking)", exc_info=True)

    return GatewayChargeResponse(
        success=True,
        remaining_balance=remaining,
        today_usage=new_today_usage,
    )


@router.get("/connections/{connection_id}", response_model=GatewayConnectionResponse)
async def get_connection(
    connection_id: UUID,
    _: None = Depends(require_gateway_key),
    db: AsyncSession = Depends(get_db),
) -> GatewayConnectionResponse:
    """Return full connection details with DECRYPTED credentials.

    Only the gateway service should call this — it needs bot_token and
    webhook_secret in plaintext to operate.
    """
    connection = await db.get(ChannelConnection, connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found.")

    decrypted_token = decrypt_value(connection.bot_token) if connection.bot_token else ""
    decrypted_secret = (
        decrypt_value(connection.webhook_secret) if connection.webhook_secret else None
    )

    blocked_result = await db.execute(
        select(ChannelContactBlock.platform_user_id_hash)
        .where(ChannelContactBlock.connection_id == connection_id)
    )
    blocked_users = [row[0] for row in blocked_result.all()]

    from src.services.channel_service import ChannelService
    return GatewayConnectionResponse(
        id=connection.id,
        owner_id=connection.owner_id,
        platform=connection.platform,
        bot_token=decrypted_token,
        webhook_secret=decrypted_secret,
        agent_id=connection.agent_id,
        skill_id=connection.skill_id,
        status=connection.status,
        daily_credit_limit=connection.daily_credit_limit,
        pause_on_limit=connection.pause_on_limit,
        low_balance_threshold=connection.low_balance_threshold,
        config=ChannelService.decrypt_config(connection.config),
        blocked_users=blocked_users,
        privacy_notice_url=connection.privacy_notice_url,
        workflow_id=connection.workflow_id,
        workflow_mappings=connection.workflow_mappings,
    )


@router.post("/heartbeat", status_code=200)
async def heartbeat(
    req: GatewayHeartbeatRequest,
    _: None = Depends(require_gateway_key),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update connection status and error_message from a gateway heartbeat.

    Expects each item in ``connections`` to have at least:
    ``{"connection_id": "<uuid>", "status": "active|paused|error", "error_message": null}``
    """
    updated = 0
    for item in req.connections:
        connection = await db.get(ChannelConnection, item.connection_id)
        if not connection:
            continue

        connection.status = item.status
        connection.error_message = item.error_message

        updated += 1

    await db.commit()
    logger.debug("Gateway heartbeat: updated %d connections", updated)
    return {"updated": updated}


@router.post("/log-message", status_code=200, dependencies=[Depends(rate_limit_by_ip)])
async def log_message(
    req: GatewayLogMessageRequest,
    _: None = Depends(require_gateway_key),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Persist a channel message record.

    Handles IntegrityError (duplicate platform_message_id) gracefully.
    """
    from decimal import Decimal

    # Encrypt outbound message text at rest (GDPR Art. 32 / SOC 2 CC6.1)
    stored_text = req.message_text
    if req.direction == "outbound" and stored_text:
        from src.core.message_crypto import encrypt_message
        try:
            stored_text = encrypt_message(stored_text)
        except Exception:
            logger.warning("Failed to encrypt outbound message — storing plaintext")

    msg = ChannelMessage(
        connection_id=req.connection_id,
        platform_user_id=req.platform_user_id,
        platform_message_id=req.platform_message_id,
        platform_chat_id=req.platform_chat_id,
        direction=req.direction,
        message_text=stored_text,
        media_type=req.media_type,
        task_id=req.task_id,
        workflow_run_id=req.workflow_run_id,
        credits_charged=Decimal(str(req.credits_charged)),
        response_time_ms=req.response_time_ms,
        error=req.error,
    )
    db.add(msg)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        logger.debug(
            "Gateway log-message: duplicate platform_message_id=%s for connection=%s",
            req.platform_message_id,
            req.connection_id,
        )
        return {"status": "duplicate"}

    logger.debug(
        "Gateway log-message: saved message connection=%s direction=%s",
        req.connection_id,
        req.direction,
    )
    return {"status": "ok"}


@router.get("/task-status/{task_id}")
async def gateway_task_status(
    task_id: UUID,
    _: None = Depends(require_gateway_key),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get task status — gateway-authenticated. Used by CF Worker to poll task completion."""
    from src.models.task import Task
    task = await db.get(Task, task_id)
    if not task:
        return {"status": "not_found"}

    status = task.status.value if hasattr(task.status, "value") else task.status
    result = {"status": status, "task_id": str(task.id)}

    if status in ("completed", "failed", "canceled"):
        result["artifacts"] = task.artifacts or []

    return result


@router.post("/create-task", status_code=201, dependencies=[Depends(rate_limit_by_ip)])
async def gateway_create_task(
    req: GatewayCreateTaskRequest,
    _: None = Depends(require_gateway_key),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a task on behalf of a channel user, authenticated via X-Gateway-Key.

    The gateway supplies ``owner_id`` (the CrewHub user whose credits fund the
    task) so that no user-facing auth token is required.  This endpoint is the
    authoritative way for the gateway service to create tasks — it avoids the
    fabricated-API-key anti-pattern and keeps gateway→backend auth consistent.
    """
    from src.schemas.task import TaskCreate, TaskMessage, MessagePart
    from src.services.task_broker import TaskBrokerService

    # If no skill_id, look up the agent's first skill
    skill_id = req.skill_id
    if not skill_id:
        from src.models.skill import AgentSkill
        skill_result = await db.execute(
            select(AgentSkill.id).where(AgentSkill.agent_id == req.provider_agent_id).limit(1)
        )
        first_skill = skill_result.scalar_one_or_none()
        skill_id = str(first_skill) if first_skill else ""

    task_data = TaskCreate(
        provider_agent_id=req.provider_agent_id,
        skill_id=skill_id,
        messages=[
            TaskMessage(
                role="user",
                parts=[MessagePart(type="text", text=req.message)],
            )
        ],
        confirmed=True,  # gateway pre-approves cost; credit check still applies
    )
    service = TaskBrokerService(db)
    task = await service.create_task(data=task_data, user_id=req.owner_id)

    # Set callback URL if provided — backend will POST result when task completes
    if req.callback_url:
        task.callback_url = req.callback_url
        await db.flush()

    logger.info(
        "Gateway create-task: task_id=%s owner=%s agent=%s callback=%s",
        task.id,
        req.owner_id,
        req.provider_agent_id,
        bool(req.callback_url),
    )
    return {"task_id": str(task.id), "status": task.status}


@router.post("/task-callback", status_code=200)
async def task_callback(
    payload: dict,
    _: None = Depends(require_gateway_key),
) -> dict:
    """Placeholder for task completion callbacks from the gateway.

    The gateway service handles forwarding results back to the platform user.
    This endpoint simply acknowledges receipt so the gateway can confirm
    delivery was accepted by the CrewHub backend.
    """
    task_id = payload.get("task_id", "<unknown>")
    status = payload.get("status", "<unknown>")
    logger.info("Gateway task-callback: task_id=%s status=%s", task_id, status)
    return {"status": "acknowledged"}


@router.post(
    "/create-workflow-run",
    response_model=GatewayCreateWorkflowRunResponse,
    status_code=201,
    dependencies=[Depends(rate_limit_by_ip)],
)
async def gateway_create_workflow_run(
    req: GatewayCreateWorkflowRunRequest,
    request: Request,
    _: None = Depends(require_gateway_key),
    db: AsyncSession = Depends(get_db),
) -> GatewayCreateWorkflowRunResponse:
    """Create a workflow run on behalf of a channel user.

    Validates the workflow exists and is accessible, checks credits, then
    dispatches the workflow execution engine.
    """
    from sqlalchemy.orm import selectinload
    from src.models.workflow import Workflow, WorkflowStep
    from src.services.workflow_execution import WorkflowExecutionService

    # Fetch connection to get the owner
    connection = await db.get(ChannelConnection, req.connection_id)
    if not connection:
        return GatewayCreateWorkflowRunResponse(
            status="error", error="Connection not found."
        )

    owner_id: UUID = connection.owner_id

    # Load workflow with steps (needed for cost estimation)
    wf_result = await db.execute(
        select(Workflow)
        .where(Workflow.id == req.workflow_id)
        .options(
            selectinload(Workflow.steps).selectinload(WorkflowStep.agent),
            selectinload(Workflow.steps).selectinload(WorkflowStep.skill),
        )
    )
    wf = wf_result.scalar_one_or_none()
    if not wf:
        return GatewayCreateWorkflowRunResponse(
            status="error", error="Workflow not found."
        )

    # Validate ownership or public access
    if wf.user_id != owner_id and not wf.is_public:
        return GatewayCreateWorkflowRunResponse(
            status="error", error="Workflow not accessible."
        )

    # Estimate credits
    exec_svc = WorkflowExecutionService(db)
    total_estimate = exec_svc._estimate_cost(wf)

    # Check balance
    ledger = CreditLedgerService(db)
    balance_info = await ledger.get_balance(owner_id)
    available = balance_info["available"]
    if total_estimate > 0 and available < total_estimate:
        return GatewayCreateWorkflowRunResponse(
            status="error",
            error=f"Insufficient credits (available: {available}, estimated: {total_estimate}).",
        )

    # Check daily limit (same pattern as /gateway/charge)
    daily_limit = connection.daily_credit_limit
    if daily_limit:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        usage_stmt = select(
            func.coalesce(func.sum(ChannelMessage.credits_charged), 0)
        ).where(
            ChannelMessage.connection_id == req.connection_id,
            ChannelMessage.created_at >= today_start,
        )
        today_usage = float((await db.execute(usage_stmt)).scalar_one())
        if (today_usage + total_estimate) > daily_limit:
            return GatewayCreateWorkflowRunResponse(
                status="error",
                error=f"Daily credit limit of {daily_limit} would be exceeded (used today: {today_usage:.2f}).",
            )

    # Execute workflow
    try:
        run = await exec_svc.execute_workflow(
            workflow_id=req.workflow_id,
            user_id=owner_id,
            input_message=req.message,
            channel_connection_id=req.connection_id,
            channel_chat_id=req.chat_id,
        )
    except Exception as exc:
        logger.exception("Gateway create-workflow-run failed: %s", exc)
        return GatewayCreateWorkflowRunResponse(
            status="error", error=str(exc)
        )

    logger.info(
        "Gateway create-workflow-run: run_id=%s workflow=%s owner=%s",
        run.id, req.workflow_id, owner_id,
    )

    # Audit log (non-blocking)
    try:
        await _audit_gateway(
            db, "create_workflow_run",
            request=request,
            target_id=str(run.id),
            new_value={
                "workflow_id": str(req.workflow_id),
                "owner": str(owner_id),
                "estimated_credits": total_estimate,
            },
        )
        await db.commit()
    except Exception:
        logger.warning("Audit log for create-workflow-run failed (non-blocking)", exc_info=True)

    return GatewayCreateWorkflowRunResponse(
        workflow_run_id=str(run.id),
        status=run.status,
        estimated_credits=float(total_estimate),
        step_count=len(wf.steps),
        workflow_name=wf.name or "",
    )


@router.get(
    "/workflow-run-status/{run_id}",
    response_model=GatewayWorkflowRunStatusResponse,
)
async def gateway_workflow_run_status(
    run_id: UUID,
    _: None = Depends(require_gateway_key),
    db: AsyncSession = Depends(get_db),
) -> GatewayWorkflowRunStatusResponse:
    """Get workflow run status — gateway-authenticated."""
    from sqlalchemy.orm import selectinload
    from src.models.workflow import WorkflowRun

    result = await db.execute(
        select(WorkflowRun)
        .where(WorkflowRun.id == run_id)
        .options(selectinload(WorkflowRun.step_runs))
    )
    run = result.scalar_one_or_none()
    if not run:
        return GatewayWorkflowRunStatusResponse(
            status="not_found", error="Workflow run not found."
        )

    # Concatenate step outputs for final_output
    final_output = None
    if run.status in ("completed", "failed"):
        outputs = []
        for sr in sorted(run.step_runs, key=lambda x: (x.step_group, x.created_at)):
            if sr.output_text:
                outputs.append(sr.output_text)
        final_output = "\n\n---\n\n".join(outputs) if outputs else None

    steps_completed = sum(1 for sr in run.step_runs if sr.status == "completed")
    snapshot = run.workflow_snapshot or {}

    return GatewayWorkflowRunStatusResponse(
        status=run.status,
        final_output=final_output,
        step_count=len(run.step_runs),
        steps_completed=steps_completed,
        total_credits_charged=float(run.total_credits_charged) if run.total_credits_charged else None,
        error=run.error,
        workflow_name=snapshot.get("name", ""),
    )


@router.get(
    "/pending-workflow-deliveries",
    response_model=GatewayPendingWorkflowDeliveriesResponse,
)
async def gateway_pending_workflow_deliveries(
    _: None = Depends(require_gateway_key),
    db: AsyncSession = Depends(get_db),
) -> GatewayPendingWorkflowDeliveriesResponse:
    """Find completed/failed workflow runs that need delivery to a channel."""
    from sqlalchemy.orm import selectinload
    from src.models.workflow import WorkflowRun

    # Find runs linked to a channel that are terminal
    runs_result = await db.execute(
        select(WorkflowRun)
        .where(
            WorkflowRun.channel_connection_id.isnot(None),
            WorkflowRun.status.in_(["completed", "failed"]),
        )
        .options(selectinload(WorkflowRun.step_runs))
        .order_by(WorkflowRun.completed_at.desc())
        .limit(50)
    )
    runs = list(runs_result.scalars().unique().all())

    if not runs:
        return GatewayPendingWorkflowDeliveriesResponse(deliveries=[])

    # Filter out runs that already have an outbound ChannelMessage with matching workflow_run_id
    run_ids = [r.id for r in runs]
    delivered_result = await db.execute(
        select(ChannelMessage.workflow_run_id)
        .where(
            ChannelMessage.workflow_run_id.in_(run_ids),
            ChannelMessage.direction == "outbound",
        )
        .distinct()
    )
    delivered_ids = {row[0] for row in delivered_result.all()}

    deliveries = []
    for run in runs:
        if run.id in delivered_ids:
            continue

        # Collect final output
        outputs = []
        for sr in sorted(run.step_runs, key=lambda x: (x.step_group, x.created_at)):
            if sr.output_text:
                outputs.append(sr.output_text)
        final_output = "\n\n---\n\n".join(outputs) if outputs else None

        # Get connection info for platform
        connection = await db.get(ChannelConnection, run.channel_connection_id)
        if not connection:
            continue

        snapshot = run.workflow_snapshot or {}

        deliveries.append(GatewayPendingWorkflowDelivery(
            run_id=str(run.id),
            connection_id=str(run.channel_connection_id),
            chat_id=run.channel_chat_id or "",
            platform=connection.platform,
            status=run.status,
            final_output=final_output,
            workflow_name=snapshot.get("name", ""),
            total_credits_charged=float(run.total_credits_charged) if run.total_credits_charged else None,
            failure_mode=snapshot.get("failure_mode", "stop"),
        ))

    return GatewayPendingWorkflowDeliveriesResponse(deliveries=deliveries)
