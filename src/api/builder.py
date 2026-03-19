# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Builder API — auth bridge, submissions, and Langflow integration."""

import hashlib
import logging
import os
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.rate_limiter import rate_limit_by_ip

from src.core.auth import get_current_user
from src.database import get_db
from src.models.submission import AgentSubmission
from src.schemas.submission import (
    SubmissionCreate,
    SubmissionListResponse,
    SubmissionResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/builder", tags=["builder"])

# Simple in-memory exchange code store (short-lived, single-use)
_exchange_codes: dict[str, dict] = {}

POOL_SPACES = [
    "https://arimatch1-crewhub-langflow-pool-02.hf.space",
    "https://arimatch1-crewhub-langflow-pool-03.hf.space",
]


class ExchangeCodeResponse(BaseModel):
    code: str
    expires_in: int
    builder_url: str


@router.post("/exchange-code", response_model=ExchangeCodeResponse)
async def create_exchange_code(
    current_user: dict = Depends(get_current_user),
):
    """Generate a short-lived exchange code for Langflow iframe auth."""
    user_id = current_user.get("id", "")

    # Generate opaque code
    raw = f"{user_id}:{time.time()}:{os.urandom(16).hex()}"
    code = hashlib.sha256(raw.encode()).hexdigest()[:32]

    # Store with 30s expiry
    _exchange_codes[code] = {
        "user_id": user_id,
        "created_at": time.time(),
        "used": False,
    }

    # Cleanup expired codes (older than 60s)
    now = time.time()
    expired = [k for k, v in _exchange_codes.items() if now - v["created_at"] > 60]
    for k in expired:
        del _exchange_codes[k]

    # Pick a pool Space (round-robin by user_id hash)
    pool_index = hash(user_id) % len(POOL_SPACES)
    builder_url = POOL_SPACES[pool_index]

    return ExchangeCodeResponse(
        code=code,
        expires_in=30,
        builder_url=builder_url,
    )


@router.post("/verify-code", dependencies=[Depends(rate_limit_by_ip)])
async def verify_exchange_code(code: str):
    """Verify an exchange code (called by Langflow middleware)."""
    entry = _exchange_codes.get(code)
    if not entry:
        raise HTTPException(status_code=401, detail="Invalid code")
    if entry["used"]:
        raise HTTPException(status_code=401, detail="Code already used")
    if time.time() - entry["created_at"] > 30:
        del _exchange_codes[code]
        raise HTTPException(status_code=401, detail="Code expired")

    entry["used"] = True
    return {"user_id": entry["user_id"], "status": "valid"}


# ---------------------------------------------------------------------------
# Submissions — submit flows for marketplace review
# ---------------------------------------------------------------------------

def _resolve_user_id(current_user: dict) -> UUID:
    uid = current_user.get("id")
    if not uid:
        raise HTTPException(status_code=401, detail="User ID not found")
    return UUID(uid) if isinstance(uid, str) else uid


@router.post("/submissions", response_model=SubmissionResponse)
async def create_submission(
    data: SubmissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Submit a Langflow flow for marketplace review."""
    user_id = _resolve_user_id(current_user)

    # Check agent limit (3 free, then paid)
    count_q = select(func.count()).select_from(
        select(AgentSubmission).where(
            AgentSubmission.user_id == user_id,
            AgentSubmission.status.in_(["pending_review", "approved"]),
        ).subquery()
    )
    current_count = (await db.execute(count_q)).scalar_one()

    if current_count >= 3:
        raise HTTPException(
            status_code=402,
            detail=f"Free trial limit reached ({current_count}/3 agents). Upgrade to Builder ($5/mo) for more.",
        )

    submission = AgentSubmission(
        user_id=user_id,
        langflow_flow_id=data.langflow_flow_id,
        name=data.name,
        description=data.description,
        category=data.category,
        credits=data.credits,
        tags=data.tags,
        status="pending_review",
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    logger.info("Submission %s created by user %s: %s", submission.id, user_id, data.name)
    return SubmissionResponse.model_validate(submission)


@router.get("/submissions", response_model=SubmissionListResponse)
async def list_submissions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List my submissions."""
    user_id = _resolve_user_id(current_user)

    total_q = select(func.count()).select_from(
        select(AgentSubmission).where(AgentSubmission.user_id == user_id).subquery()
    )
    total = (await db.execute(total_q)).scalar_one()

    stmt = (
        select(AgentSubmission)
        .where(AgentSubmission.user_id == user_id)
        .order_by(AgentSubmission.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    submissions = result.scalars().all()

    return SubmissionListResponse(
        submissions=[SubmissionResponse.model_validate(s) for s in submissions],
        total=total,
    )


@router.delete("/submissions/{submission_id}")
async def delete_submission(
    submission_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete/unpublish a submission (user-initiated)."""
    user_id = _resolve_user_id(current_user)
    submission = await db.get(AgentSubmission, submission_id)

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your submission")

    await db.delete(submission)
    await db.commit()
    return {"status": "deleted"}
