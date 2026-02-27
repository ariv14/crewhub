"""Tests for main application middleware and configuration."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_body_size_limit(client: AsyncClient):
    """Requests declaring Content-Length > 10MB should be rejected with 413."""
    resp = await client.post(
        "/api/v1/agents/",
        headers={"content-length": "999999999"},
        content=b"x",
    )
    assert resp.status_code == 413
    assert resp.json()["detail"] == "Request body too large"


@pytest.mark.asyncio
async def test_revoke_api_key(client: AsyncClient, auth_headers: dict[str, str]):
    """After revoking an API key, it should no longer authenticate."""
    # Create an API key
    create_resp = await client.post(
        "/api/v1/auth/api-keys",
        json={"name": "test-key"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    api_key = create_resp.json()["key"]

    # Verify the key works
    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"X-API-Key": api_key},
    )
    assert me_resp.status_code == 200

    # Revoke the key
    revoke_resp = await client.post(
        "/api/v1/auth/revoke-api-key",
        headers=auth_headers,
    )
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["detail"] == "API key revoked"

    # Verify the key no longer works
    me_resp2 = await client.get(
        "/api/v1/auth/me",
        headers={"X-API-Key": api_key},
    )
    assert me_resp2.status_code == 401


@pytest.mark.asyncio
async def test_weak_password_rejected(client: AsyncClient):
    """Registration with a weak password should return 422."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": "abc", "name": "Weak"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_password_missing_uppercase_rejected(client: AsyncClient):
    """Password without uppercase letter should be rejected."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "noup@example.com", "password": "alllowercase1", "name": "No Up"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_strong_password_accepted(client: AsyncClient):
    """Registration with a strong password should succeed."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "strong@example.com", "password": "SecurePass1", "name": "Strong"},
    )
    assert resp.status_code == 201
