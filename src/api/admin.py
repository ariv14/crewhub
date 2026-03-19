# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Admin-only endpoints for platform governance.

All endpoints require authentication and is_admin=True on the user record.
Includes: platform stats, user/agent management, credit grants, re-embedding.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.audit import audit_log
from src.core.auth import get_current_user
from src.core.rate_limiter import rate_limit_by_ip
from src.database import get_db
from src.models.agent import Agent
from src.models.task import Task
from src.models.transaction import Transaction
from src.models.user import User
from src.schemas.agent import AgentResponse, AgentStatus, VerificationLevel
from src.schemas.auth import UserResponse
from src.schemas.task import TaskResponse, TaskListResponse
from src.schemas.credits import TransactionListResponse, TransactionResponse

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Bootstrap: promote caller to admin when no admins exist yet
# ---------------------------------------------------------------------------


@router.post("/bootstrap", dependencies=[Depends(rate_limit_by_ip)])
async def bootstrap_admin(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """One-time self-promotion to admin — only works when no admins exist."""
    admin_count = (
        await db.execute(select(func.count()).where(User.is_admin.is_(True)))
    ).scalar_one()
    if admin_count > 0:
        raise HTTPException(status_code=403, detail="Admin already exists")

    firebase_uid = current_user.get("firebase_uid")
    if firebase_uid:
        result = await db.execute(
            select(User).where(User.firebase_uid == firebase_uid)
        )
    else:
        result = await db.execute(
            select(User).where(User.id == UUID(current_user["id"]))
        )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    user.is_admin = True
    user.admin_role = "super_admin"
    await audit_log(db, action="admin.bootstrap", actor_user_id=str(user.id), target_type="user", target_id=user.id, new_value={"is_admin": True, "admin_role": "super_admin"}, request=request)
    await db.flush()
    return {"message": f"{user.email} is now admin"}


# ---------------------------------------------------------------------------
# Admin guard dependency
# ---------------------------------------------------------------------------


async def require_admin(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency that verifies the current user is an admin."""
    firebase_uid = current_user.get("firebase_uid")
    if firebase_uid:
        result = await db.execute(
            select(User).where(User.firebase_uid == firebase_uid)
        )
    else:
        result = await db.execute(
            select(User).where(User.id == UUID(current_user["id"]))
        )

    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def require_ops_or_super(admin: User = Depends(require_admin)) -> User:
    """Require ops_admin or super_admin role."""
    if admin.admin_role not in ("super_admin", "ops_admin") and admin.admin_role is not None:
        raise HTTPException(status_code=403, detail="Requires ops_admin or super_admin role")
    return admin


async def require_billing_or_super(admin: User = Depends(require_admin)) -> User:
    """Require billing_admin or super_admin role."""
    if admin.admin_role not in ("super_admin", "billing_admin") and admin.admin_role is not None:
        raise HTTPException(status_code=403, detail="Requires billing_admin or super_admin role")
    return admin


# ---------------------------------------------------------------------------
# Agent Submissions — review queue
# ---------------------------------------------------------------------------


@router.get("/submissions", tags=["admin"])
async def list_pending_submissions(
    status: str = Query("pending_review"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin: "User" = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List agent submissions for review."""
    from src.models.submission import AgentSubmission
    from src.schemas.submission import SubmissionResponse

    total_q = select(func.count()).select_from(
        select(AgentSubmission).where(AgentSubmission.status == status).subquery()
    )
    total = (await db.execute(total_q)).scalar_one()

    stmt = (
        select(AgentSubmission)
        .where(AgentSubmission.status == status)
        .order_by(AgentSubmission.created_at.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    submissions = result.scalars().all()

    return {
        "submissions": [SubmissionResponse.model_validate(s) for s in submissions],
        "total": total,
    }


@router.post("/submissions/{submission_id}/approve", tags=["admin"])
async def approve_submission(
    submission_id: UUID,
    request: Request,
    admin: "User" = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Approve a submission — registers it as a marketplace agent."""
    from datetime import datetime, timezone
    from src.models.submission import AgentSubmission

    submission = await db.get(AgentSubmission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.status != "pending_review":
        raise HTTPException(status_code=400, detail=f"Cannot approve: status is {submission.status}")

    # Create agent record with Langflow proxy endpoint
    import os
    import re
    proxy_base = os.getenv("LANGFLOW_PROXY_BASE", "https://api.crewhubai.com")
    endpoint = f"{proxy_base}/langflow/run/{submission.langflow_flow_id}"

    agent = Agent(
        owner_id=submission.user_id,
        name=submission.name,
        description=submission.description or "",
        endpoint=endpoint,
        category=submission.category or "general",
        tags=submission.tags or [],
        pricing={"model": "per_task", "credits": submission.credits, "license_type": "commercial"},
        status="active",
    )
    db.add(agent)
    await db.flush()

    # Auto-generate primary skill with embedding for discoverability
    try:
        from src.models.skill import AgentSkill
        from src.core.embeddings import EmbeddingService

        skill_key = re.sub(r"[^a-z0-9-]", "-", submission.name.lower()).strip("-")[:50]
        skill_desc = submission.description or f"A {submission.category or 'general'} agent built with CrewHub Builder"
        skill_text = f"{submission.name}: {skill_desc}"

        embed_svc = EmbeddingService()
        embedding = await embed_svc.generate(skill_text)

        skill = AgentSkill(
            agent_id=agent.id,
            skill_key=skill_key or "default",
            name=submission.name,
            description=skill_desc,
            input_modes=["text"],
            output_modes=["text"],
            examples=[],
            embedding=embedding,
        )
        db.add(skill)
        await db.flush()
    except Exception as _skill_err:
        import logging
        logging.getLogger(__name__).warning("Skill creation failed during approval: %s", _skill_err)

    # Update submission
    submission.status = "approved"
    submission.reviewed_by = admin.id
    submission.reviewed_at = datetime.now(timezone.utc)
    submission.agent_id = agent.id

    await audit_log(db, action="admin.approve_submission", actor_user_id=str(admin.id), target_type="submission", target_id=submission_id, new_value={"agent_id": str(agent.id)}, request=request)
    await db.commit()
    return {"status": "approved", "agent_id": str(agent.id), "submission_id": str(submission_id)}


@router.post("/submissions/{submission_id}/reject", tags=["admin"])
async def reject_submission(
    submission_id: UUID,
    request: Request,
    admin: "User" = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    notes: str = Query(..., min_length=1, description="Reason for rejection"),
):
    """Reject a submission with reviewer notes."""
    from datetime import datetime, timezone
    from src.models.submission import AgentSubmission

    submission = await db.get(AgentSubmission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.status != "pending_review":
        raise HTTPException(status_code=400, detail=f"Cannot reject: status is {submission.status}")

    submission.status = "rejected"
    submission.reviewer_notes = notes
    submission.reviewed_by = admin.id
    submission.reviewed_at = datetime.now(timezone.utc)

    await audit_log(db, action="admin.reject_submission", actor_user_id=str(admin.id), target_type="submission", target_id=submission_id, new_value={"notes": notes}, request=request)
    await db.commit()
    return {"status": "rejected", "submission_id": str(submission_id)}


@router.post("/submissions/{submission_id}/revoke", tags=["admin"])
async def revoke_submission(
    submission_id: UUID,
    request: Request,
    admin: "User" = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a previously approved submission — takes agent offline."""
    from datetime import datetime, timezone
    from src.models.submission import AgentSubmission

    submission = await db.get(AgentSubmission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.status != "approved":
        raise HTTPException(status_code=400, detail=f"Cannot revoke: status is {submission.status}")

    # Deactivate the agent
    if submission.agent_id:
        agent = await db.get(Agent, submission.agent_id)
        if agent:
            agent.status = "inactive"

    submission.status = "revoked"
    submission.reviewed_at = datetime.now(timezone.utc)

    await audit_log(db, action="admin.revoke_submission", actor_user_id=str(admin.id), target_type="submission", target_id=submission_id, request=request)
    await db.commit()
    return {"status": "revoked", "submission_id": str(submission_id)}


# ---------------------------------------------------------------------------
# Bulk pricing update
# ---------------------------------------------------------------------------


class PricingUpdate(BaseModel):
    agent_id: UUID
    credits: float = Field(ge=0)


class BulkPricingRequest(BaseModel):
    updates: list[PricingUpdate]


@router.post("/bulk-pricing", tags=["admin"])
async def bulk_update_pricing(
    data: BulkPricingRequest,
    request: Request,
    admin: "User" = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update pricing for multiple agents at once. Admin only."""
    results = []
    for update in data.updates:
        agent = await db.get(Agent, update.agent_id)
        if not agent:
            results.append({"id": str(update.agent_id), "status": "not_found"})
            continue
        pricing = agent.pricing or {}
        old = pricing.get("credits", 0)
        pricing["credits"] = update.credits
        agent.pricing = pricing
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(agent, "pricing")
        results.append({
            "id": str(update.agent_id),
            "name": agent.name,
            "old_credits": old,
            "new_credits": update.credits,
            "status": "updated",
        })
    await audit_log(db, action="admin.bulk_pricing", actor_user_id=str(admin.id), target_type="agents", new_value={"count": len(data.updates)}, request=request)
    await db.commit()
    return {"updated": len([r for r in results if r["status"] == "updated"]), "results": results}


# ---------------------------------------------------------------------------
# Platform stats
# ---------------------------------------------------------------------------


class PlatformStats(BaseModel):
    total_users: int
    active_users: int
    total_agents: int
    active_agents: int
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    total_transaction_volume: float


@router.get("/stats", response_model=PlatformStats)
async def get_platform_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> PlatformStats:
    """Aggregated platform KPIs."""
    total_users = (await db.execute(select(func.count(User.id)))).scalar_one()
    active_users = (
        await db.execute(select(func.count(User.id)).where(User.is_active.is_(True)))
    ).scalar_one()

    total_agents = (await db.execute(select(func.count(Agent.id)))).scalar_one()
    active_agents = (
        await db.execute(
            select(func.count(Agent.id)).where(Agent.status == "active")
        )
    ).scalar_one()

    total_tasks = (await db.execute(select(func.count(Task.id)))).scalar_one()
    completed_tasks = (
        await db.execute(
            select(func.count(Task.id)).where(Task.status == "completed")
        )
    ).scalar_one()
    failed_tasks = (
        await db.execute(
            select(func.count(Task.id)).where(Task.status == "failed")
        )
    ).scalar_one()

    vol_result = await db.execute(select(func.coalesce(func.sum(Transaction.amount), 0)))
    total_volume = float(vol_result.scalar_one())

    return PlatformStats(
        total_users=total_users,
        active_users=active_users,
        total_agents=total_agents,
        active_agents=active_agents,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        failed_tasks=failed_tasks,
        total_transaction_volume=total_volume,
    )


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------


class AdminUserListResponse(BaseModel):
    users: list[UserResponse]
    total: int


@router.get("/users/", response_model=AdminUserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUserListResponse:
    """List all platform users (admin only)."""
    total = (await db.execute(select(func.count(User.id)))).scalar_one()
    offset = (page - 1) * per_page
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(offset).limit(per_page)
    )
    users = [UserResponse.model_validate(u) for u in result.scalars().all()]
    return AdminUserListResponse(users=users, total=total)


class UserStatusUpdate(BaseModel):
    is_active: bool | None = None
    is_admin: bool | None = None
    account_tier: str | None = None  # "free" or "premium"


@router.put("/users/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    user_id: UUID,
    data: UserStatusUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Activate/deactivate a user, grant/revoke admin, or set account tier (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    await audit_log(db, action="admin.update_user_status", actor_user_id=str(admin.id), target_type="user", target_id=user_id, old_value={"is_active": user.is_active, "is_admin": user.is_admin}, new_value=data.model_dump(exclude_none=True), request=request)
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.is_admin is not None:
        user.is_admin = data.is_admin
    if data.account_tier is not None:
        if data.account_tier not in ("free", "premium"):
            raise HTTPException(status_code=400, detail="account_tier must be 'free' or 'premium'")
        user.account_tier = data.account_tier
    await db.flush()
    return UserResponse.model_validate(user)


# ---------------------------------------------------------------------------
# All tasks (not user-scoped)
# ---------------------------------------------------------------------------


@router.get("/tasks/", response_model=TaskListResponse)
async def list_all_tasks(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> TaskListResponse:
    """List all tasks across the platform (admin only)."""
    query = select(Task)
    if status:
        query = query.where(Task.status == status)

    total = (
        await db.execute(select(func.count()).select_from(query.subquery()))
    ).scalar_one()

    offset = (page - 1) * per_page
    result = await db.execute(
        query.order_by(Task.created_at.desc()).offset(offset).limit(per_page)
    )
    tasks = [TaskResponse.model_validate(t) for t in result.scalars().all()]
    return TaskListResponse(tasks=tasks, total=total)


# ---------------------------------------------------------------------------
# All transactions
# ---------------------------------------------------------------------------


@router.get("/transactions/", response_model=TransactionListResponse)
async def list_all_transactions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    type: str | None = Query(None, description="Filter by transaction type"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> TransactionListResponse:
    """List all transactions across the platform (admin only)."""
    query = select(Transaction)
    if type:
        query = query.where(Transaction.type == type)

    total = (
        await db.execute(select(func.count()).select_from(query.subquery()))
    ).scalar_one()

    offset = (page - 1) * per_page
    result = await db.execute(
        query.order_by(Transaction.created_at.desc()).offset(offset).limit(per_page)
    )
    txns = [TransactionResponse.model_validate(t) for t in result.scalars().all()]
    return TransactionListResponse(transactions=txns, total=total)


# ---------------------------------------------------------------------------
# Agent admin control
# ---------------------------------------------------------------------------


class AgentStatusUpdate(BaseModel):
    status: AgentStatus


@router.put("/agents/{agent_id}/status", response_model=AgentResponse)
async def update_agent_status(
    agent_id: UUID,
    data: AgentStatusUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Override agent status (suspend/activate) — admin only."""
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id).options(selectinload(Agent.skills))
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    await audit_log(db, action="admin.update_agent_status", actor_user_id=str(admin.id), target_type="agent", target_id=agent_id, old_value={"status": agent.status}, new_value={"status": data.status.value}, request=request)
    agent.status = data.status.value
    await db.flush()
    await db.refresh(agent)
    return AgentResponse.model_validate(agent)


class AgentPricingUpdate(BaseModel):
    pricing: dict


@router.put("/agents/{agent_id}/pricing", response_model=AgentResponse)
async def update_agent_pricing(
    agent_id: UUID,
    data: AgentPricingUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Override agent pricing — admin only."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    await audit_log(db, action="admin.update_agent_pricing", actor_user_id=str(admin.id), target_type="agent", target_id=agent_id, old_value={"pricing": agent.pricing}, new_value={"pricing": data.pricing}, request=request)
    agent.pricing = data.pricing
    await db.commit()
    await db.refresh(agent)
    return AgentResponse.model_validate(agent)


class AgentVerificationUpdate(BaseModel):
    verification_level: VerificationLevel


@router.put("/agents/{agent_id}/verification", response_model=AgentResponse)
async def update_agent_verification(
    agent_id: UUID,
    data: AgentVerificationUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Override agent verification level — admin only."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    await audit_log(db, action="admin.update_agent_verification", actor_user_id=str(admin.id), target_type="agent", target_id=agent_id, old_value={"verification_level": agent.verification_level}, new_value={"verification_level": data.verification_level.value}, request=request)
    agent.verification_level = data.verification_level.value
    await db.flush()
    return AgentResponse.model_validate(agent)


# ---------------------------------------------------------------------------
# Credit grants (admin only)
# ---------------------------------------------------------------------------


class AdminCreditGrant(BaseModel):
    user_id: UUID
    amount: float = Field(gt=0, le=100000)
    reason: str = Field(min_length=3, max_length=200)


@router.post("/credits/grant")
async def grant_credits(
    data: AdminCreditGrant,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Grant bonus credits to a user (admin only).

    Credits are added as BONUS type — spendable but never withdrawable
    via Stripe Connect payouts.
    """
    from src.services.credit_ledger import CreditLedgerService

    # Verify target user exists
    target = await db.get(User, data.user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target user not found")

    ledger = CreditLedgerService(db)
    txn = await ledger.grant_bonus(
        owner_id=data.user_id,
        amount=data.amount,
        description=f"Admin grant: {data.reason}",
    )
    await audit_log(db, action="admin.grant_credits", actor_user_id=str(admin.id), target_type="user", target_id=data.user_id, new_value={"amount": data.amount, "reason": data.reason}, request=request)
    return {
        "transaction_id": str(txn.id),
        "amount": data.amount,
        "user_id": str(data.user_id),
        "reason": data.reason,
    }


# ---------------------------------------------------------------------------
# Re-embed all skills (admin only)
# ---------------------------------------------------------------------------


@router.post("/re-embed-skills")
async def re_embed_skills(
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Re-generate embeddings for all skills using current embedding provider.

    Use this after switching from FakeProvider to a real provider (OpenAI, etc.)
    to replace hash-based vectors with semantically meaningful ones.
    """
    from src.core.embeddings import EmbeddingService
    from src.models.skill import AgentSkill

    embed_svc = EmbeddingService()  # uses platform key or provider config

    result = await db.execute(select(AgentSkill))
    skills = list(result.scalars().all())

    texts = [f"{s.name}: {s.description}" for s in skills]
    if not texts:
        return {"message": "No skills found", "updated": 0}

    embeddings = await embed_svc.generate_batch(texts)
    for skill, emb in zip(skills, embeddings):
        skill.embedding = emb

    await audit_log(db, action="admin.re_embed_skills", actor_user_id=str(admin.id), new_value={"skills_count": len(skills)}, request=request)
    await db.commit()
    return {"message": f"Re-embedded {len(skills)} skills", "updated": len(skills)}
