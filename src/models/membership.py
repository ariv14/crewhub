"""Membership model — user ↔ organization/team roles."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class MembershipRole(str, enum.Enum):
    VIEWER = "viewer"
    MEMBER = "member"
    ADMIN = "admin"
    OWNER = "owner"

    @staticmethod
    def hierarchy() -> list[str]:
        return ["viewer", "member", "admin", "owner"]

    def __ge__(self, other: "MembershipRole") -> bool:
        h = self.hierarchy()
        return h.index(self.value) >= h.index(other.value)

    def __gt__(self, other: "MembershipRole") -> bool:
        h = self.hierarchy()
        return h.index(self.value) > h.index(other.value)

    def __le__(self, other: "MembershipRole") -> bool:
        h = self.hierarchy()
        return h.index(self.value) <= h.index(other.value)

    def __lt__(self, other: "MembershipRole") -> bool:
        h = self.hierarchy()
        return h.index(self.value) < h.index(other.value)


class Membership(Base):
    __tablename__ = "memberships"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True
    )
    role: Mapped[MembershipRole] = mapped_column(
        String(20), nullable=False, default=MembershipRole.MEMBER
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="memberships")
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="memberships"
    )
    team: Mapped["Team | None"] = relationship("Team", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Membership(user={self.user_id}, org={self.organization_id}, role={self.role})>"
