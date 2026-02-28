"""Tests for F7: Onboarding Wizard — user onboarding flow."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_new_user_onboarding_not_completed(
    client: AsyncClient, auth_headers: dict
):
    """Freshly registered user should have onboarding_completed=false."""
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["onboarding_completed"] is False


@pytest.mark.asyncio
async def test_complete_onboarding(client: AsyncClient, auth_headers: dict):
    """POST /auth/onboarding with name + interests → 200."""
    resp = await client.post(
        "/api/v1/auth/onboarding",
        json={"name": "Onboarded User", "interests": ["summarization", "translation"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["onboarding_completed"] is True


@pytest.mark.asyncio
async def test_onboarding_sets_flag(client: AsyncClient, auth_headers: dict):
    """After completing onboarding, GET /auth/me should show the flag set."""
    await client.post(
        "/api/v1/auth/onboarding",
        json={"name": "Flagged User", "interests": ["code-review"]},
        headers=auth_headers,
    )

    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["onboarding_completed"] is True


@pytest.mark.asyncio
async def test_onboarding_stores_interests(client: AsyncClient, auth_headers: dict):
    """After completing onboarding, interests should be persisted in profile."""
    interests = ["translation", "summarization", "code-review"]
    await client.post(
        "/api/v1/auth/onboarding",
        json={"interests": interests},
        headers=auth_headers,
    )

    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["interests"] == interests
