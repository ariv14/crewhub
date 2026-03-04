"""Authentication endpoints: registration, login, token management, and API keys.

Supports two modes:
- Firebase Auth (production): Frontend sends Firebase ID token, backend verifies
  and creates/syncs local user record.
- Local JWT (dev/testing): Traditional email/password registration and login.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
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

DEFAULT_SIGNUP_BONUS = 100.0



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
    name = decoded.get("name", email.split("@")[0])

    # Check if user already exists (by email)
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        # First-time login — create local user record
        user = User(
            email=email,
            hashed_password="firebase-managed",  # No local password needed
            name=name,
            firebase_uid=firebase_uid,
        )
        db.add(user)
        await db.flush()

        # Provision credits account with signup bonus
        ledger = CreditLedgerService(db)
        await ledger.get_or_create_account(user.id)
        await db.flush()
    elif not user.firebase_uid:
        # Existing user linking to Firebase for the first time
        user.firebase_uid = firebase_uid
        await db.flush()

    return UserResponse.model_validate(user)


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
