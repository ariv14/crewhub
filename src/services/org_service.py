# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Business logic for organizations, teams, and memberships."""

import uuid
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.membership import Membership, MembershipRole
from src.models.organization import Organization
from src.models.team import Team
from src.models.user import User


# ── Helpers ───────────────────────────────────────────────────

async def require_org_role(
    db: AsyncSession, user_id: uuid.UUID, org_id: uuid.UUID, min_role: MembershipRole
) -> Membership:
    """Return the user's membership if role >= min_role, else 403."""
    result = await db.execute(
        select(Membership).where(
            Membership.user_id == user_id,
            Membership.organization_id == org_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of this organization")
    if not MembershipRole(membership.role) >= min_role:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires at least {min_role.value} role")
    return membership


# ── Organizations ─────────────────────────────────────────────

async def create_organization(
    db: AsyncSession, name: str, slug: str, owner_id: uuid.UUID, avatar_url: str | None = None
) -> Organization:
    # Check slug uniqueness
    exists = await db.execute(select(Organization).where(Organization.slug == slug))
    if exists.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Slug already in use")

    org = Organization(name=name, slug=slug, avatar_url=avatar_url)
    db.add(org)
    await db.flush()

    # Creator becomes owner
    membership = Membership(
        user_id=owner_id, organization_id=org.id, role=MembershipRole.OWNER
    )
    db.add(membership)
    await db.commit()
    await db.refresh(org)
    return org


async def list_user_organizations(
    db: AsyncSession, user_id: uuid.UUID
) -> tuple[Sequence[Organization], int]:
    # Get orgs where user is a member
    result = await db.execute(
        select(Organization)
        .join(Membership, Membership.organization_id == Organization.id)
        .where(Membership.user_id == user_id)
        .order_by(Organization.name)
    )
    orgs = result.scalars().all()
    return orgs, len(orgs)


async def get_organization(db: AsyncSession, org_id: uuid.UUID) -> Organization:
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    return org


async def update_organization(
    db: AsyncSession, org_id: uuid.UUID, **kwargs: object
) -> Organization:
    org = await get_organization(db, org_id)
    for key, value in kwargs.items():
        if value is not None:
            setattr(org, key, value)
    await db.commit()
    await db.refresh(org)
    return org


async def delete_organization(db: AsyncSession, org_id: uuid.UUID) -> None:
    org = await get_organization(db, org_id)
    await db.delete(org)
    await db.commit()


# ── Teams ─────────────────────────────────────────────────────

async def create_team(
    db: AsyncSession, org_id: uuid.UUID, name: str, description: str | None = None
) -> Team:
    team = Team(organization_id=org_id, name=name, description=description)
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return team


async def list_teams(
    db: AsyncSession, org_id: uuid.UUID
) -> tuple[Sequence[Team], int]:
    result = await db.execute(
        select(Team).where(Team.organization_id == org_id).order_by(Team.name)
    )
    teams = result.scalars().all()
    return teams, len(teams)


async def get_team(db: AsyncSession, team_id: uuid.UUID) -> Team:
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team not found")
    return team


async def update_team(
    db: AsyncSession, team_id: uuid.UUID, **kwargs: object
) -> Team:
    team = await get_team(db, team_id)
    for key, value in kwargs.items():
        if value is not None:
            setattr(team, key, value)
    await db.commit()
    await db.refresh(team)
    return team


async def delete_team(db: AsyncSession, team_id: uuid.UUID) -> None:
    team = await get_team(db, team_id)
    await db.delete(team)
    await db.commit()


# ── Memberships ───────────────────────────────────────────────

async def add_member(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_email: str,
    role: str = "member",
    team_id: uuid.UUID | None = None,
) -> Membership:
    # Find user by email
    result = await db.execute(select(User).where(User.email == user_email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found with that email")

    # Check not already a member
    existing = await db.execute(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.organization_id == org_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "User is already a member")

    membership = Membership(
        user_id=user.id,
        organization_id=org_id,
        team_id=team_id,
        role=MembershipRole(role),
    )
    db.add(membership)
    await db.commit()
    await db.refresh(membership)
    return membership


async def list_members(
    db: AsyncSession, org_id: uuid.UUID
) -> tuple[Sequence[Membership], int]:
    result = await db.execute(
        select(Membership).where(Membership.organization_id == org_id)
    )
    members = result.scalars().all()
    return members, len(members)


async def update_member_role(
    db: AsyncSession, membership_id: uuid.UUID, new_role: str
) -> Membership:
    result = await db.execute(
        select(Membership).where(Membership.id == membership_id)
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Membership not found")

    # Prevent demoting the last owner
    if MembershipRole(membership.role) == MembershipRole.OWNER:
        count_result = await db.execute(
            select(func.count()).where(
                Membership.organization_id == membership.organization_id,
                Membership.role == MembershipRole.OWNER.value,
            )
        )
        if count_result.scalar_one() <= 1 and new_role != "owner":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Cannot remove the last owner"
            )

    membership.role = MembershipRole(new_role)
    await db.commit()
    await db.refresh(membership)
    return membership


async def remove_member(db: AsyncSession, membership_id: uuid.UUID) -> None:
    result = await db.execute(
        select(Membership).where(Membership.id == membership_id)
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Membership not found")

    # Prevent removing the last owner
    if MembershipRole(membership.role) == MembershipRole.OWNER:
        count_result = await db.execute(
            select(func.count()).where(
                Membership.organization_id == membership.organization_id,
                Membership.role == MembershipRole.OWNER.value,
            )
        )
        if count_result.scalar_one() <= 1:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Cannot remove the last owner"
            )

    await db.delete(membership)
    await db.commit()
