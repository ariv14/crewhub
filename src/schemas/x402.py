"""Schemas for x402 payment verification."""

from typing import Optional
from pydantic import BaseModel, Field


class X402ReceiptSubmit(BaseModel):
    """Client submits this after paying via x402."""
    tx_hash: str = Field(max_length=128, description="On-chain transaction hash")
    chain: str = Field(max_length=20, description="Blockchain network (e.g. base, solana)")
    token: str = Field(max_length=20, description="Token symbol (e.g. USDC)")
    amount: float = Field(ge=0, description="Amount paid in token units")
    payer: str = Field(max_length=128, description="Payer wallet address")
    payee: str = Field(max_length=128, description="Payee wallet address")


class X402PaymentRequest(BaseModel):
    """Returned to client when task requires x402 payment."""
    task_id: str
    amount_usdc: float
    recipient_wallet: str = ""
    facilitator_url: str = ""
    supported_chains: list[str] = []
    supported_tokens: list[str] = []
    expires_in_minutes: int = 10


class X402ReceiptResponse(BaseModel):
    """Response after receipt verification."""
    verified: bool
    tx_hash: str
    task_status: str
    detail: Optional[str] = None
