# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Authentication endpoints: registration, login, token management, and API keys.

Supports two modes:
- Firebase Auth (production): Frontend sends Firebase ID token, backend verifies
  and creates/syncs local user record.
- Local JWT (dev/testing): Traditional email/password registration and login.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import (
    create_access_token,
    generate_api_key,
    get_current_user,
    hash_password,
    is_firebase_enabled,
    verify_firebase_token,
    verify_password,
)
from src.core.exceptions import ConflictError, UnauthorizedError
from src.core.rate_limiter import rate_limit_by_ip
from src.database import get_db
from src.models.user import User
from src.schemas.auth import (
    ApiKeyCreate,
    ApiKeyResponse,
    OnboardingComplete,
    Token,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from src.services.credit_ledger import CreditLedgerService

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Firebase Auth flow — used in production
# ---------------------------------------------------------------------------


class FirebaseTokenRequest(BaseModel):
    """Request body for Firebase token exchange."""
    id_token: str


@router.post("/firebase", response_model=UserResponse, status_code=200,
               dependencies=[Depends(rate_limit_by_ip)])
async def firebase_auth(
    data: FirebaseTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Authenticate with a Firebase ID token.

    If the user doesn't exist locally, creates a new user record and provisions
    a credits account. If the user already exists, returns the existing profile.

    This is the primary auth endpoint in production. The frontend obtains a
    Firebase ID token via Firebase Auth SDK (Google/GitHub OAuth) and sends it here.
    """
    decoded = verify_firebase_token(data.id_token)
    firebase_uid = decoded.get("uid")
    email = decoded.get("email", "")
    name = decoded.get("name", "") or (email.split("@")[0] if email else f"user-{firebase_uid[:8]}")

    # Look up by firebase_uid first (handles provider changes / private emails),
    # then fall back to email lookup for legacy users
    result = await db.execute(
        select(User).where(User.firebase_uid == firebase_uid)
    )
    user = result.scalar_one_or_none()

    if user is None and email:
        # Check by email for legacy users not yet linked to Firebase
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    if user is None:
        # First-time login — create local user record
        # GitHub users may have private emails; use firebase_uid as fallback
        user_email = email or f"{firebase_uid}@github.firebaseuser"
        user = User(
            email=user_email,
            hashed_password="firebase-managed",  # No local password needed
            name=name,
            firebase_uid=firebase_uid,
        )
        db.add(user)
        try:
            await db.flush()
        except IntegrityError:
            # Concurrent request already created this user — roll back and re-fetch
            await db.rollback()
            result = await db.execute(
                select(User).where(User.firebase_uid == firebase_uid)
            )
            user = result.scalar_one_or_none()
            if user is None:
                raise HTTPException(status_code=500, detail="User creation conflict")
            return UserResponse.model_validate(user)

        # Provision credits account with signup bonus
        ledger = CreditLedgerService(db)
        await ledger.get_or_create_account(user.id)
        await db.flush()
    else:
        # Update firebase_uid if not yet linked
        if not user.firebase_uid:
            user.firebase_uid = firebase_uid
        # Update email if user had a placeholder and now provides a real one
        if email and user.email.endswith("@github.firebaseuser"):
            user.email = email
        if email and not user.name:
            user.name = name
        await db.flush()

    return UserResponse.model_validate(user)


# ---------------------------------------------------------------------------
# Session cookie management — httpOnly cookie for XSS-resistant auth
# ---------------------------------------------------------------------------

SESSION_COOKIE_NAME = "__session"


def _session_cookie_kwargs() -> dict:
    """Cookie parameters for the httpOnly session cookie."""
    from src.config import settings
    return {
        "key": SESSION_COOKIE_NAME,
        "httponly": True,
        "secure": True,
        "samesite": "lax",
        "path": "/",
        "max_age": 3600,
        "domain": ".crewhubai.com" if not settings.debug else None,
    }


@router.post("/session", response_model=UserResponse, status_code=200,
             dependencies=[Depends(rate_limit_by_ip)])
async def create_session(
    data: FirebaseTokenRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Exchange Firebase ID token for httpOnly session cookie.

    Sets a Secure, HttpOnly, SameSite=Lax cookie that the browser sends
    automatically on subsequent requests. This replaces localStorage token
    storage to prevent XSS-based token theft.
    """
    decoded = verify_firebase_token(data.id_token)
    firebase_uid = decoded.get("uid")
    email = decoded.get("email", "")
    name = decoded.get("name", "") or (email.split("@")[0] if email else f"user-{firebase_uid[:8]}")

    result = await db.execute(
        select(User).where(User.firebase_uid == firebase_uid)
    )
    user = result.scalar_one_or_none()

    if user is None and email:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    if user is None:
        user_email = email or f"{firebase_uid}@github.firebaseuser"
        user = User(
            email=user_email,
            hashed_password="firebase-managed",
            name=name,
            firebase_uid=firebase_uid,
        )
        db.add(user)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            result = await db.execute(
                select(User).where(User.firebase_uid == firebase_uid)
            )
            user = result.scalar_one_or_none()
            if user is None:
                raise HTTPException(status_code=500, detail="User creation conflict")
            response.set_cookie(value=data.id_token, **_session_cookie_kwargs())
            return UserResponse.model_validate(user)

        ledger = CreditLedgerService(db)
        await ledger.get_or_create_account(user.id)
        await db.flush()
    else:
        if not user.firebase_uid:
            user.firebase_uid = firebase_uid
        if email and user.email.endswith("@github.firebaseuser"):
            user.email = email
        if email and not user.name:
            user.name = name
        await db.flush()

    response.set_cookie(value=data.id_token, **_session_cookie_kwargs())
    return UserResponse.model_validate(user)


@router.post("/session/logout", status_code=200)
async def logout_session(response: Response):
    """Clear the httpOnly session cookie."""
    response.delete_cookie(**{k: v for k, v in _session_cookie_kwargs().items() if k != "max_age"})
    return {"message": "Logged out"}


# ---------------------------------------------------------------------------
# Local auth flow — used in dev/testing (when Firebase is not configured)
# ---------------------------------------------------------------------------


@router.post("/register", response_model=UserResponse, status_code=201,
               dependencies=[Depends(rate_limit_by_ip)])
async def register(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Register a new user account (local dev/testing mode).

    In production, use /auth/firebase instead — users authenticate via
    Firebase Auth (Google/GitHub OAuth) and accounts are auto-created.
    """
    if is_firebase_enabled():
        raise HTTPException(
            status_code=403,
            detail="Local registration is disabled when Firebase Auth is configured. "
            "Use /auth/firebase instead.",
        )

    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError(detail="A user with this email already exists")

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        name=data.name,
    )
    db.add(user)
    await db.flush()

    ledger = CreditLedgerService(db)
    await ledger.get_or_create_account(user.id)
    await db.flush()

    return UserResponse.model_validate(user)


@router.post("/login", response_model=Token,
               dependencies=[Depends(rate_limit_by_ip)])
async def login(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Authenticate with email/password and return a JWT (local dev/testing mode).

    In production, the frontend uses Firebase Auth SDK to get an ID token directly.
    """
    if is_firebase_enabled():
        raise HTTPException(
            status_code=403,
            detail="Local login is disabled when Firebase Auth is configured. "
            "Use Firebase Auth SDK instead.",
        )

    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(data.password, user.hashed_password):
        raise UnauthorizedError(detail="Invalid email or password")

    if not user.is_active:
        raise UnauthorizedError(detail="Account is deactivated")

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    return Token(access_token=access_token)


# ---------------------------------------------------------------------------
# Common endpoints (work with both auth modes)
# ---------------------------------------------------------------------------


@router.get("/me", response_model=UserResponse)
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    # Look up by firebase_uid first (primary in production), then by local UUID
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
        raise UnauthorizedError(detail="User not found")
    return UserResponse.model_validate(user)


@router.put("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> UserResponse:
    """Update the profile of the currently authenticated user."""
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
        raise UnauthorizedError(detail="User not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    await db.flush()
    return UserResponse.model_validate(user)


@router.post("/onboarding", response_model=UserResponse)
async def complete_onboarding(
    data: OnboardingComplete,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> UserResponse:
    """Complete the onboarding flow for a new user."""
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
        raise UnauthorizedError(detail="User not found")

    if data.name:
        user.name = data.name
    user.interests = data.interests
    user.onboarding_completed = True
    await db.flush()
    return UserResponse.model_validate(user)


@router.post("/api-keys", response_model=ApiKeyResponse, status_code=201)
async def create_api_key(
    data: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> ApiKeyResponse:
    """Generate a new API key for the authenticated user.

    The plain-text key is returned only once in this response.
    Replaces any existing API key for this user.
    """
    from src.core._api_key_lookup import hash_api_key

    # Look up by firebase_uid first, then by local UUID
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
        raise UnauthorizedError(detail="User not found")

    plain_key = generate_api_key()
    user.api_key_hash = hash_api_key(plain_key)
    await db.flush()

    return ApiKeyResponse(
        key=plain_key,
        name=data.name,
        created_at=datetime.now(timezone.utc),
    )


@router.post("/revoke-api-key")
async def revoke_api_key(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Revoke the current user's API key so it can no longer be used."""
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
        raise UnauthorizedError(detail="User not found")

    user.api_key_revoked_at = datetime.now(timezone.utc)
    await db.flush()
    return {"detail": "API key revoked"}


# ---------------------------------------------------------------------------
# Debug-only: generate a token for E2E testing (DEBUG mode only)
# ---------------------------------------------------------------------------

from src.config import settings as _settings  # noqa: E402

if _settings.debug:
    @router.post("/debug-token")
    async def debug_token(
        db: AsyncSession = Depends(get_db),
    ):
        """Generate a JWT + API key for E2E testing. Only available in DEBUG mode.

        Creates or reuses a test user (e2e@crewhub.dev) and returns both
        a short-lived JWT and a persistent API key.
        """
        email = "e2e@crewhub.dev"
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                email=email,
                hashed_password="debug-managed",
                name="E2E Test User",
            )
            db.add(user)
            await db.flush()
            ledger = CreditLedgerService(db)
            await ledger.get_or_create_account(user.id)

        jwt = create_access_token({"sub": str(user.id)})

        # Generate API key if not already present
        api_key = None
        if not user.api_key_hash or user.api_key_revoked_at:
            plain_key = generate_api_key()
            from src.core._api_key_lookup import hash_api_key
            user.api_key_hash = hash_api_key(plain_key)
            user.api_key_revoked_at = None
            api_key = plain_key
            await db.flush()

        return {
            "token": jwt,
            "api_key": api_key,
            "user_id": str(user.id),
            "note": "API key is only shown on first generation. Store it securely.",
        }


# ---------------------------------------------------------------------------
# GDPR Data Export (Article 15 / Article 20)
# ---------------------------------------------------------------------------


@router.get("/me/export", dependencies=[Depends(rate_limit_by_ip)])
async def export_my_data(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Export all personal data as JSON (GDPR Article 20 — data portability)."""
    from src.models.task import Task
    from src.models.transaction import Transaction
    from src.models.agent import Agent
    from src.models.workflow import Workflow

    # Resolve DB user
    firebase_uid = current_user.get("firebase_uid")
    if firebase_uid:
        result = await db.execute(select(User).where(User.firebase_uid == firebase_uid))
    else:
        result = await db.execute(select(User).where(User.id == UUID(current_user["id"])))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Agents
    agents_result = await db.execute(select(Agent).where(Agent.owner_id == user.id))
    agents = [
        {"id": str(a.id), "name": a.name, "description": a.description, "status": a.status,
         "category": a.category, "created_at": a.created_at.isoformat() if a.created_at else None}
        for a in agents_result.scalars().all()
    ]

    # Tasks (cap 500)
    tasks_result = await db.execute(
        select(Task).where(Task.creator_user_id == user.id)
        .order_by(Task.created_at.desc()).limit(500)
    )
    tasks_list = tasks_result.scalars().all()
    tasks = [
        {"id": str(t.id), "status": t.status.value if hasattr(t.status, "value") else t.status,
         "credits_charged": float(t.credits_charged) if t.credits_charged else None,
         "created_at": t.created_at.isoformat() if t.created_at else None}
        for t in tasks_list
    ]

    # Transactions (cap 1000) — join via account
    if user.account:
        from sqlalchemy import or_
        account_id = user.account.id
        txns_result = await db.execute(
            select(Transaction).where(
                or_(Transaction.from_account_id == account_id, Transaction.to_account_id == account_id)
            ).order_by(Transaction.created_at.desc()).limit(1000)
        )
        txns = [
            {"id": str(tx.id), "type": tx.type.value if hasattr(tx.type, "value") else tx.type,
             "amount": float(tx.amount), "description": tx.description,
             "created_at": tx.created_at.isoformat() if tx.created_at else None}
            for tx in txns_result.scalars().all()
        ]
    else:
        txns = []

    # Workflows
    wf_result = await db.execute(select(Workflow).where(Workflow.owner_id == user.id))
    workflows = [
        {"id": str(w.id), "name": w.name, "is_public": w.is_public,
         "created_at": w.created_at.isoformat() if w.created_at else None}
        for w in wf_result.scalars().all()
    ]

    # LLM key providers (names only, never values)
    llm_providers = list(user.llm_api_keys.keys()) if user.llm_api_keys else []

    import json as json_mod
    from fastapi.responses import Response as JSONFileResponse
    export = {
        "export_generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1",
        "profile": {
            "id": str(user.id), "email": user.email, "name": user.name,
            "account_tier": user.account_tier, "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "consent": {
            "version": user.consent_version, "given_at": user.consent_given_at.isoformat() if user.consent_given_at else None,
        },
        "api_key_metadata": {"has_key": bool(user.api_key_hash), "revoked": bool(user.api_key_revoked_at)},
        "llm_key_providers": llm_providers,
        "credit_balance": float(user.account.balance) if user.account else 0,
        "agents": agents,
        "tasks": {"items": tasks, "count": len(tasks), "truncated": len(tasks_list) >= 500},
        "transactions": {"items": txns, "count": len(txns), "truncated": len(txns) >= 1000},
        "workflows": workflows,
    }
    return JSONFileResponse(
        content=json_mod.dumps(export, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="crewhub-export-{datetime.now().strftime("%Y-%m-%d")}.json"'},
    )


# ---------------------------------------------------------------------------
# GDPR Account Deletion (Article 17)
# ---------------------------------------------------------------------------


class DeleteAccountRequest(BaseModel):
    confirmation: str


@router.delete("/me")
async def delete_my_account(
    data: DeleteAccountRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete account and scrub PII (GDPR Article 17 — right to erasure).

    Requires {"confirmation": "DELETE"} in the request body.
    PII is scrubbed immediately. Account is deactivated. Transactions retained for compliance.
    """
    if data.confirmation != "DELETE":
        raise HTTPException(status_code=400, detail='Confirmation must be exactly "DELETE"')

    import hashlib as hl
    from src.core.audit import audit_log

    firebase_uid = current_user.get("firebase_uid")
    if firebase_uid:
        result = await db.execute(select(User).where(User.firebase_uid == firebase_uid))
    else:
        result = await db.execute(select(User).where(User.id == UUID(current_user["id"])))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.deletion_requested_at:
        raise HTTPException(status_code=409, detail="Account deletion already requested")

    # Audit log before scrubbing
    await audit_log(db, action="gdpr.account_deletion", actor_user_id=str(user.id),
                    target_type="user", target_id=user.id)

    # Scrub PII immediately
    email_hash = hl.sha256(user.email.encode()).hexdigest()[:12]
    user.email = f"deleted-{email_hash}@deleted.crewhub"
    user.name = "Deleted User"
    user.hashed_password = "deleted"
    user.firebase_uid = None
    user.llm_api_keys = None
    user.stripe_customer_id = None
    user.stripe_subscription_id = None
    user.stripe_connect_account_id = None
    user.api_key_hash = None
    user.is_active = False
    user.deletion_requested_at = datetime.now(timezone.utc)

    await db.flush()

    # Clear httpOnly session cookie
    from src.api.auth import _session_cookie_kwargs
    response.delete_cookie(**{k: v for k, v in _session_cookie_kwargs().items() if k != "max_age"})

    return {"message": "Account deletion processed. PII has been scrubbed. Transactions retained for compliance."}
