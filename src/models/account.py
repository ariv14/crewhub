# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(16, 4), nullable=False, default=Decimal("0"), server_default="0"
    )
    reserved: Mapped[Decimal] = mapped_column(
        Numeric(16, 4), nullable=False, default=Decimal("0"), server_default="0"
    )
    currency: Mapped[str] = mapped_column(
        String(20), nullable=False, default="CREDITS", server_default="CREDITS"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="account", lazy="selectin")
    outgoing_transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="from_account", foreign_keys="[Transaction.from_account_id]", lazy="noload"
    )
    incoming_transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="to_account", foreign_keys="[Transaction.to_account_id]", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Account(id={self.id}, balance={self.balance}, currency={self.currency})>"
