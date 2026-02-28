import uuid
from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import JSON, Boolean, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    firebase_uid: Mapped[Optional[str]] = mapped_column(
        String(128), unique=True, nullable=True, index=True
    )
    # Account tier: "free" (rate-limited) or "premium" (unlimited)
    account_tier: Mapped[str] = mapped_column(
        String(20), nullable=False, default="free", server_default="free"
    )
    api_key_hash: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )
    api_key_revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    # User's LLM API keys (encrypted), keyed by provider name.
    # Format: {"openai": "<encrypted>", "gemini": "<encrypted>", ...}
    llm_api_keys: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=sa.true())
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default=sa.false())
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=sa.false())
    interests: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    agents: Mapped[list["Agent"]] = relationship("Agent", back_populates="owner", lazy="selectin")
    account: Mapped["Account"] = relationship("Account", back_populates="owner", uselist=False, lazy="selectin")
    memberships: Mapped[list["Membership"]] = relationship(
        "Membership", back_populates="user", lazy="noload", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, name={self.name})>"
