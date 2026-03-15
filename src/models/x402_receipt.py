# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Verified x402 payment receipts — replay attack prevention."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class X402VerifiedReceipt(Base):
    __tablename__ = "x402_verified_receipts"

    tx_hash: Mapped[str] = mapped_column(String(128), primary_key=True)
    chain: Mapped[str] = mapped_column(String(20), nullable=False)
    token: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    payer: Mapped[str] = mapped_column(String(128), nullable=False)
    payee: Mapped[str] = mapped_column(String(128), nullable=False)
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<X402VerifiedReceipt(tx_hash={self.tx_hash}, amount={self.amount})>"
