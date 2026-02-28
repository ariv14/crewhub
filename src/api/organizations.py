"""Organization, team, and membership management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.database import get_db
from src.models.membership import MembershipRole
from src.models.user import User
from src.schemas.organization import (
    MembershipCreate,
    MembershipListResponse,
    MembershipResponse,
    MembershipUpdate,
    OrganizationCreate,
    OrganizationListResponse,
    OrganizationResponse,
    OrganizationUpdate,
    TeamCreate,
    TeamListResponse,
    TeamResponse,
    TeamUpdate,
)
from src.services.org_service import (
    add_member,
    create_organization,
    create_team,
    delete_organization,
    delete_team,
    get_organization,
    get_team,
    list_members,
    list_teams,
    list_user_organizations,
    remove_member,
    require_org_role,
    update_member_role,
    update_organization,
    update_team,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])


# ── Organization CRUD ─────────────────────────────────────────

@router.post("/", response_model=OrganizationResponse, status_code=201)
async def create_org(
    body: OrganizationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_organization(db, body.name, body.slug, user.id, body.avatar_url)


@router.get("/", response_model=OrganizationListResponse)
async def list_orgs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    orgs, total = await list_user_organizations(db, user.id)
    return OrganizationListResponse(organizations=orgs, total=total)


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_org(
    org_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_org_role(db, user.id, org_id, MembershipRole.VIEWER)
    return await get_organization(db, org_id)


@router.patch("/{org_id}", response_model=OrganizationResponse)
async def patch_org(
    org_id: UUID,
    body: OrganizationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_org_role(db, user.id, org_id, MembershipRole.ADMIN)
    return await update_organization(db, org_id, **body.model_dump(exclude_unset=True))


@router.delete("/{org_id}", status_code=204)
async def delete_org(
    org_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_org_role(db, user.id, org_id, MembershipRole.OWNER)
    await delete_organization(db, org_id)


# ── Team CRUD ─────────────────────────────────────────────────

@router.post("/{org_id}/teams", response_model=TeamResponse, status_code=201)
async def create_org_team(
    org_id: UUID,
    body: TeamCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_org_role(db, user.id, org_id, MembershipRole.ADMIN)
    return await create_team(db, org_id, body.name, body.description)


@router.get("/{org_id}/teams", response_model=TeamListResponse)
async def list_org_teams(
    org_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_org_role(db, user.id, org_id, MembershipRole.VIEWER)
    teams, total = await list_teams(db, org_id)
    return TeamListResponse(teams=teams, total=total)


@router.get("/{org_id}/teams/{team_id}", response_model=TeamResponse)
async def get_org_team(
    org_id: UUID,
    team_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_org_role(db, user.id, org_id, MembershipRole.VIEWER)
    return await get_team(db, team_id)


@router.patch("/{org_id}/teams/{team_id}", response_model=TeamResponse)
async def patch_org_team(
    org_id: UUID,
    team_id: UUID,
    body: TeamUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_org_role(db, user.id, org_id, MembershipRole.ADMIN)
    return await update_team(db, team_id, **body.model_dump(exclude_unset=True))


@router.delete("/{org_id}/teams/{team_id}", status_code=204)
async def delete_org_team(
    org_id: UUID,
    team_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_org_role(db, user.id, org_id, MembershipRole.ADMIN)
    await delete_team(db, team_id)


# ── Membership CRUD ───────────────────────────────────────────

@router.post("/{org_id}/members", response_model=MembershipResponse, status_code=201)
async def invite_member(
    org_id: UUID,
    body: MembershipCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_org_role(db, user.id, org_id, MembershipRole.ADMIN)
    membership = await add_member(db, org_id, body.user_email, body.role, body.team_id)
    return MembershipResponse(
        id=membership.id,
        user_id=membership.user_id,
        organization_id=membership.organization_id,
        team_id=membership.team_id,
        role=membership.role.value if isinstance(membership.role, MembershipRole) else membership.role,
        created_at=membership.created_at,
        user_email=body.user_email,
    )


@router.get("/{org_id}/members", response_model=MembershipListResponse)
async def list_org_members(
    org_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_org_role(db, user.id, org_id, MembershipRole.VIEWER)
    members, total = await list_members(db, org_id)
    responses = []
    for m in members:
        responses.append(MembershipResponse(
            id=m.id,
            user_id=m.user_id,
            organization_id=m.organization_id,
            team_id=m.team_id,
            role=m.role.value if isinstance(m.role, MembershipRole) else m.role,
            created_at=m.created_at,
        ))
    return MembershipListResponse(members=responses, total=total)


@router.patch("/{org_id}/members/{membership_id}", response_model=MembershipResponse)
async def update_member(
    org_id: UUID,
    membership_id: UUID,
    body: MembershipUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_org_role(db, user.id, org_id, MembershipRole.ADMIN)
    membership = await update_member_role(db, membership_id, body.role)
    return MembershipResponse(
        id=membership.id,
        user_id=membership.user_id,
        organization_id=membership.organization_id,
        team_id=membership.team_id,
        role=membership.role.value if isinstance(membership.role, MembershipRole) else membership.role,
        created_at=membership.created_at,
    )


@router.delete("/{org_id}/members/{membership_id}", status_code=204)
async def remove_org_member(
    org_id: UUID,
    membership_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_org_role(db, user.id, org_id, MembershipRole.OWNER)
    await remove_member(db, membership_id)
