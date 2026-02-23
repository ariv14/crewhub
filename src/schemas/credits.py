from enum import Enum
from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TransactionType(str, Enum):
    purchase = "purchase"
    task_payment = "task_payment"
    refund = "refund"
    bonus = "bonus"
    platform_fee = "platform_fee"


class BalanceResponse(BaseModel):
    balance: float
    reserved: float
    available: float
    currency: str


class PurchaseRequest(BaseModel):
    amount: float = Field(gt=0)


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    from_account_id: Optional[UUID] = None
    to_account_id: Optional[UUID] = None
    amount: float
    type: TransactionType
    task_id: Optional[UUID] = None
    description: str
    created_at: datetime


class TransactionListResponse(BaseModel):
    transactions: list[TransactionResponse]
    total: int


class UsageResponse(BaseModel):
    total_spent: float
    total_earned: float
    tasks_created: int
    tasks_received: int
    period: str
