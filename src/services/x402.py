"""x402 payment verification service."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.x402_receipt import X402VerifiedReceipt
from src.schemas.x402 import X402ReceiptSubmit


class X402PaymentService:
    """Verifies x402 payment receipts and prevents replay attacks."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @property
    def supported_chains(self) -> set[str]:
        return {c.strip().lower() for c in settings.x402_supported_chains.split(",") if c.strip()}

    @property
    def supported_tokens(self) -> set[str]:
        return {t.strip().upper() for t in settings.x402_supported_tokens.split(",") if t.strip()}

    async def check_replay(self, tx_hash: str) -> bool:
        """Return True if this tx_hash has already been verified (replay)."""
        stmt = select(X402VerifiedReceipt).where(X402VerifiedReceipt.tx_hash == tx_hash)
        result = await self.db.execute(stmt)
        return result.scalars().first() is not None

    async def record_receipt(self, task_id: UUID, receipt: X402ReceiptSubmit) -> X402VerifiedReceipt:
        """Store a verified receipt in the database."""
        record = X402VerifiedReceipt(
            tx_hash=receipt.tx_hash,
            chain=receipt.chain,
            token=receipt.token,
            amount=Decimal(str(receipt.amount)),
            payer=receipt.payer,
            payee=receipt.payee,
            task_id=task_id,
        )
        self.db.add(record)
        await self.db.flush()
        return record

    def validate_receipt(self, receipt: X402ReceiptSubmit, required_amount: float) -> list[str]:
        """Validate receipt fields. Returns list of error messages (empty = valid)."""
        errors = []
        if receipt.chain.lower() not in self.supported_chains:
            errors.append(
                f"Unsupported chain '{receipt.chain}'. "
                f"Supported: {', '.join(sorted(self.supported_chains))}"
            )
        if receipt.token.upper() not in self.supported_tokens:
            errors.append(
                f"Unsupported token '{receipt.token}'. "
                f"Supported: {', '.join(sorted(self.supported_tokens))}"
            )
        if receipt.amount < required_amount:
            errors.append(
                f"Insufficient amount: {receipt.amount} < {required_amount} required"
            )
        return errors

    async def verify_with_facilitator(self, receipt: X402ReceiptSubmit) -> bool:
        """Call the x402 facilitator API to verify the receipt on-chain.
        Returns True if verified, False otherwise.
        Falls back to True (optimistic) if no facilitator is configured (dev mode).
        """
        if not settings.x402_facilitator_url:
            return True
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{settings.x402_facilitator_url}/verify",
                    json={
                        "tx_hash": receipt.tx_hash,
                        "chain": receipt.chain,
                        "token": receipt.token,
                        "amount": receipt.amount,
                        "payer": receipt.payer,
                        "payee": receipt.payee,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("verified", False)
                return False
        except httpx.HTTPError:
            return False
