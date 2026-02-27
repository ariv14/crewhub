import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class TransactionType(str, enum.Enum):
    PURCHASE = "purchase"
    TASK_PAYMENT = "task_payment"
    REFUND = "refund"
    BONUS = "bonus"
    PLATFORM_FEE = "platform_fee"
    X402_PAYMENT = "x402_payment"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    from_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    to_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    type: Mapped[TransactionType] = mapped_column(
        String(20), nullable=False, index=True
    )
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    from_account: Mapped[Optional["Account"]] = relationship(
        "Account", back_populates="outgoing_transactions", foreign_keys=[from_account_id], lazy="selectin"
    )
    to_account: Mapped[Optional["Account"]] = relationship(
        "Account", back_populates="incoming_transactions", foreign_keys=[to_account_id], lazy="selectin"
    )
    task: Mapped[Optional["Task"]] = relationship(
        "Task", back_populates="transactions", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, type={self.type}, amount={self.amount})>"
