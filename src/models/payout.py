# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class PayoutStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PayoutRequest(Base):
    __tablename__ = "payout_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount_credits: Mapped[float] = mapped_column(
        Numeric(16, 4), nullable=False
    )
    amount_usd_cents: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    stripe_fee_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    status: Mapped[PayoutStatus] = mapped_column(
        String(20), nullable=False, default=PayoutStatus.PENDING, index=True
    )
    stripe_transfer_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True
    )
    failure_reason: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return f"<PayoutRequest(id={self.id}, credits={self.amount_credits}, status={self.status})>"
