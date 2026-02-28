"""Tests for F8: Org/Team RBAC — organizations, teams, and membership management."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# ── Helpers ──────────────────────────────────────────────────────


async def _create_org(
    client: AsyncClient, headers: dict, name: str = "Test Org", slug: str | None = None
) -> dict:
    slug = slug or f"test-org-{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        "/api/v1/organizations/",
        json={"name": name, "slug": slug},
        headers=headers,
    )
    assert resp.status_code == 201, f"Org creation failed: {resp.text}"
    return resp.json()


# ── Organization CRUD ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_organization(client: AsyncClient, auth_headers: dict):
    data = await _create_org(client, auth_headers, name="My Org")

    assert data["name"] == "My Org"
    assert data["id"]
    assert data["slug"]


@pytest.mark.asyncio
async def test_list_organizations(client: AsyncClient, auth_headers: dict):
    await _create_org(client, auth_headers, name="Org A")
    await _create_org(client, auth_headers, name="Org B")

    resp = await client.get("/api/v1/organizations/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2


@pytest.mark.asyncio
async def test_get_organization(client: AsyncClient, auth_headers: dict):
    org = await _create_org(client, auth_headers)

    resp = await client.get(f"/api/v1/organizations/{org['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == org["id"]


@pytest.mark.asyncio
async def test_delete_organization(client: AsyncClient, auth_headers: dict):
    org = await _create_org(client, auth_headers)

    del_resp = await client.delete(
        f"/api/v1/organizations/{org['id']}", headers=auth_headers
    )
    assert del_resp.status_code == 204

    get_resp = await client.get(
        f"/api/v1/organizations/{org['id']}", headers=auth_headers
    )
    # After delete, either 404 or 403 (no membership anymore)
    assert get_resp.status_code in (403, 404)


# ── Team CRUD ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_team(client: AsyncClient, auth_headers: dict):
    org = await _create_org(client, auth_headers)

    resp = await client.post(
        f"/api/v1/organizations/{org['id']}/teams",
        json={"name": "Engineering"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Engineering"


@pytest.mark.asyncio
async def test_list_teams(client: AsyncClient, auth_headers: dict):
    org = await _create_org(client, auth_headers)

    await client.post(
        f"/api/v1/organizations/{org['id']}/teams",
        json={"name": "Team A"},
        headers=auth_headers,
    )
    await client.post(
        f"/api/v1/organizations/{org['id']}/teams",
        json={"name": "Team B"},
        headers=auth_headers,
    )

    resp = await client.get(
        f"/api/v1/organizations/{org['id']}/teams", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 2


@pytest.mark.asyncio
async def test_delete_team(client: AsyncClient, auth_headers: dict):
    org = await _create_org(client, auth_headers)

    team_resp = await client.post(
        f"/api/v1/organizations/{org['id']}/teams",
        json={"name": "Temp Team"},
        headers=auth_headers,
    )
    team_id = team_resp.json()["id"]

    del_resp = await client.delete(
        f"/api/v1/organizations/{org['id']}/teams/{team_id}",
        headers=auth_headers,
    )
    assert del_resp.status_code == 204


# ── Membership CRUD ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invite_member(
    client: AsyncClient, auth_headers: dict, second_auth_headers: dict
):
    org = await _create_org(client, auth_headers)

    # Get second user's email
    me_resp = await client.get("/api/v1/auth/me", headers=second_auth_headers)
    second_email = me_resp.json()["email"]

    resp = await client.post(
        f"/api/v1/organizations/{org['id']}/members",
        json={"user_email": second_email, "role": "member"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "member"


@pytest.mark.asyncio
async def test_list_members(
    client: AsyncClient, auth_headers: dict, second_auth_headers: dict
):
    org = await _create_org(client, auth_headers)

    me_resp = await client.get("/api/v1/auth/me", headers=second_auth_headers)
    second_email = me_resp.json()["email"]

    await client.post(
        f"/api/v1/organizations/{org['id']}/members",
        json={"user_email": second_email, "role": "member"},
        headers=auth_headers,
    )

    resp = await client.get(
        f"/api/v1/organizations/{org['id']}/members", headers=auth_headers
    )
    assert resp.status_code == 200
    # Owner + invited member = at least 2
    assert resp.json()["total"] >= 2


@pytest.mark.asyncio
async def test_update_member_role(
    client: AsyncClient, auth_headers: dict, second_auth_headers: dict
):
    org = await _create_org(client, auth_headers)

    me_resp = await client.get("/api/v1/auth/me", headers=second_auth_headers)
    second_email = me_resp.json()["email"]

    invite_resp = await client.post(
        f"/api/v1/organizations/{org['id']}/members",
        json={"user_email": second_email, "role": "member"},
        headers=auth_headers,
    )
    membership_id = invite_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/organizations/{org['id']}/members/{membership_id}",
        json={"role": "admin"},
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_remove_member(
    client: AsyncClient, auth_headers: dict, second_auth_headers: dict
):
    org = await _create_org(client, auth_headers)

    me_resp = await client.get("/api/v1/auth/me", headers=second_auth_headers)
    second_email = me_resp.json()["email"]

    invite_resp = await client.post(
        f"/api/v1/organizations/{org['id']}/members",
        json={"user_email": second_email, "role": "member"},
        headers=auth_headers,
    )
    membership_id = invite_resp.json()["id"]

    del_resp = await client.delete(
        f"/api/v1/organizations/{org['id']}/members/{membership_id}",
        headers=auth_headers,
    )
    assert del_resp.status_code == 204


# ── RBAC Enforcement ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_viewer_cannot_create_team(
    client: AsyncClient, auth_headers: dict, second_auth_headers: dict
):
    org = await _create_org(client, auth_headers)

    me_resp = await client.get("/api/v1/auth/me", headers=second_auth_headers)
    second_email = me_resp.json()["email"]

    # Invite as viewer
    await client.post(
        f"/api/v1/organizations/{org['id']}/members",
        json={"user_email": second_email, "role": "viewer"},
        headers=auth_headers,
    )

    # Viewer tries to create team → 403
    resp = await client.post(
        f"/api/v1/organizations/{org['id']}/teams",
        json={"name": "Forbidden Team"},
        headers=second_auth_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_non_member_cannot_access_org(
    client: AsyncClient, auth_headers: dict, second_auth_headers: dict
):
    org = await _create_org(client, auth_headers)

    # Second user (no membership) tries to access org
    resp = await client.get(
        f"/api/v1/organizations/{org['id']}", headers=second_auth_headers
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_slug_uniqueness(client: AsyncClient, auth_headers: dict):
    slug = f"unique-slug-{uuid.uuid4().hex[:6]}"
    await _create_org(client, auth_headers, slug=slug)

    # Same slug again → 409
    resp = await client.post(
        "/api/v1/organizations/",
        json={"name": "Duplicate Org", "slug": slug},
        headers=auth_headers,
    )
    assert resp.status_code == 409
