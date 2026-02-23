"""Authentication endpoints: registration, login, token management, and API keys.

Supports two modes:
- Firebase Auth (production): Frontend sends Firebase ID token, backend verifies
  and creates/syncs local user record.
- Local JWT (dev/testing): Traditional email/password registration and login.
"""

from datetime import datetime
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
from src.database import get_db
from src.models.user import User
from src.schemas.auth import (
    ApiKeyCreate,
    ApiKeyResponse,
    Token,
    UserCreate,
    UserResponse,
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


@router.post("/firebase", response_model=UserResponse, status_code=200)
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


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Register a new user account (local dev/testing mode).

    In production, use /auth/firebase instead — users authenticate via
    Firebase Auth (Google/GitHub OAuth) and accounts are auto-created.
    """
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


@router.post("/login", response_model=Token)
async def login(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Authenticate with email/password and return a JWT (local dev/testing mode).

    In production, the frontend uses Firebase Auth SDK to get an ID token directly.
    """
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
    user_id = current_user["id"]

    # Firebase UID is a string, not UUID — look up by firebase_uid or by id
    if is_firebase_enabled() and current_user.get("firebase_uid"):
        result = await db.execute(
            select(User).where(User.firebase_uid == current_user["firebase_uid"])
        )
    else:
        result = await db.execute(select(User).where(User.id == UUID(user_id)))

    user = result.scalar_one_or_none()
    if user is None:
        raise UnauthorizedError(detail="User not found")
    return UserResponse.model_validate(user)


@router.post("/api-keys", response_model=ApiKeyResponse, status_code=201)
async def create_api_key(
    data: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> ApiKeyResponse:
    """Generate a new API key for the authenticated user.

    The plain-text key is returned only once in this response.
    """
    plain_key = generate_api_key()

    return ApiKeyResponse(
        key=plain_key,
        name=data.name,
        created_at=datetime.utcnow(),
    )
