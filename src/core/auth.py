"""Authentication and authorization utilities using Firebase Auth."""

import json
import secrets
from uuid import UUID

import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

from src.config import settings
from src.core.exceptions import UnauthorizedError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Firebase initialization
# ---------------------------------------------------------------------------

_firebase_app = None


def _init_firebase():
    """Initialize Firebase Admin SDK (idempotent)."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    if firebase_admin._apps:
        _firebase_app = firebase_admin.get_app()
        return _firebase_app

    cred = None
    if settings.firebase_credentials_json:
        # Accept either a file path or a JSON string
        try:
            cred_data = json.loads(settings.firebase_credentials_json)
            cred = credentials.Certificate(cred_data)
        except (json.JSONDecodeError, ValueError):
            # Treat as file path
            cred = credentials.Certificate(settings.firebase_credentials_json)

    if cred:
        _firebase_app = firebase_admin.initialize_app(cred)
    elif settings.firebase_project_id:
        # Running on Cloud Run — uses default credentials (no key file needed)
        _firebase_app = firebase_admin.initialize_app(
            options={"projectId": settings.firebase_project_id}
        )
    else:
        # Local dev without Firebase — will use fallback JWT mode
        _firebase_app = None

    return _firebase_app


def is_firebase_enabled() -> bool:
    """Check if Firebase Auth is configured and available."""
    _init_firebase()
    return _firebase_app is not None


# ---------------------------------------------------------------------------
# Password hashing (still used for API keys)
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# Firebase token verification
# ---------------------------------------------------------------------------


def verify_firebase_token(id_token: str) -> dict:
    """Verify a Firebase ID token and return the decoded claims.

    Returns:
        Dict with 'uid', 'email', 'name', etc.

    Raises:
        UnauthorizedError: If token is invalid or expired.
    """
    if not is_firebase_enabled():
        raise UnauthorizedError(detail="Firebase Auth not configured")

    try:
        decoded = firebase_auth.verify_id_token(id_token)
        return decoded
    except firebase_auth.InvalidIdTokenError:
        raise UnauthorizedError(detail="Invalid Firebase token")
    except firebase_auth.ExpiredIdTokenError:
        raise UnauthorizedError(detail="Firebase token expired")
    except firebase_auth.RevokedIdTokenError:
        raise UnauthorizedError(detail="Firebase token revoked")
    except Exception as exc:
        raise UnauthorizedError(detail=f"Firebase auth error: {exc}")


# ---------------------------------------------------------------------------
# Fallback JWT (for local dev / testing without Firebase)
# ---------------------------------------------------------------------------


def create_access_token(data: dict) -> str:
    """Create a signed JWT for local dev/testing (when Firebase is not configured).

    In production, Firebase Auth issues tokens — this is only used as a fallback.
    """
    from datetime import datetime, timedelta, timezone
    from jose import jwt

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=60)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    """Decode a local JWT (fallback when Firebase is not configured)."""
    from jose import JWTError, jwt

    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError as exc:
        raise UnauthorizedError(detail="Invalid or expired token") from exc


# ---------------------------------------------------------------------------
# API key generation
# ---------------------------------------------------------------------------


def generate_api_key() -> str:
    """Generate a secure random API key prefixed with 'a2a_'."""
    return f"a2a_{secrets.token_hex(32)}"


# ---------------------------------------------------------------------------
# FastAPI auth dependency
# ---------------------------------------------------------------------------


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> dict:
    """Extract the current user from a Firebase ID token, fallback JWT, or API key.

    Priority: Bearer token → API key.

    For Bearer tokens:
    - If Firebase is configured: verifies as Firebase ID token
    - If Firebase is not configured: verifies as local JWT (dev/test mode)

    Returns:
        dict with 'id' (UUID str or Firebase UID), 'email', and optionally 'firebase_uid'.
    """
    # Try Bearer token first
    if credentials is not None:
        token = credentials.credentials

        if is_firebase_enabled():
            # Production mode: Firebase Auth
            decoded = verify_firebase_token(token)
            return {
                "id": decoded.get("uid"),
                "email": decoded.get("email", ""),
                "name": decoded.get("name", ""),
                "firebase_uid": decoded.get("uid"),
            }
        else:
            # Dev/test mode: local JWT
            payload = decode_access_token(token)
            user_id = payload.get("sub")
            if user_id is None:
                raise UnauthorizedError(detail="Token missing subject claim")
            return {"id": user_id, "email": payload.get("email", "")}

    # Fall back to API key
    if x_api_key is not None:
        try:
            from src.core._api_key_lookup import lookup_user_by_api_key
            user = await lookup_user_by_api_key(x_api_key)
            if user is not None:
                return user
        except ImportError:
            pass

    raise UnauthorizedError(detail="Authentication required")


async def get_current_user_id(
    current_user: dict = Depends(get_current_user),
) -> UUID:
    """FastAPI dependency that returns just the current user's UUID."""
    return UUID(current_user["id"])
