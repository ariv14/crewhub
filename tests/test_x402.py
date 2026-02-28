"""Tests for x402 payment verification service."""

import pytest
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.x402 import X402PaymentService
from src.models.x402_receipt import X402VerifiedReceipt
from src.schemas.x402 import X402ReceiptSubmit


@pytest.mark.asyncio
async def test_check_replay_returns_false_for_new_hash(db_session: AsyncSession):
    """A never-seen tx_hash should not be flagged as replay."""
    svc = X402PaymentService(db_session)
    assert await svc.check_replay("0xabc123") is False


@pytest.mark.asyncio
async def test_check_replay_returns_true_for_existing_hash(db_session: AsyncSession):
    """A previously recorded tx_hash should be flagged as replay."""
    receipt = X402VerifiedReceipt(
        tx_hash="0xabc123",
        chain="base",
        token="USDC",
        amount=Decimal("10.0"),
        payer="0xpayer",
        payee="0xpayee",
        task_id=None,
    )
    db_session.add(receipt)
    await db_session.flush()

    svc = X402PaymentService(db_session)
    assert await svc.check_replay("0xabc123") is True


@pytest.mark.asyncio
async def test_record_receipt_stores_in_db(db_session: AsyncSession):
    """Recording a receipt should persist it to the database."""
    svc = X402PaymentService(db_session)
    receipt_data = X402ReceiptSubmit(
        tx_hash="0xdef456",
        chain="base",
        token="USDC",
        amount=10.0,
        payer="0xpayer",
        payee="0xpayee",
    )
    await svc.record_receipt(task_id=None, receipt=receipt_data)
    assert await svc.check_replay("0xdef456") is True


@pytest.mark.asyncio
async def test_validate_receipt_rejects_unsupported_chain(db_session: AsyncSession):
    """Should reject receipts on unsupported chains."""
    svc = X402PaymentService(db_session)
    receipt = X402ReceiptSubmit(
        tx_hash="0x111", chain="ethereum", token="USDC",
        amount=10.0, payer="0xp", payee="0xr",
    )
    errors = svc.validate_receipt(receipt, required_amount=10.0)
    assert any("chain" in e.lower() for e in errors)


@pytest.mark.asyncio
async def test_validate_receipt_rejects_insufficient_amount(db_session: AsyncSession):
    """Should reject receipts with amount less than required."""
    svc = X402PaymentService(db_session)
    receipt = X402ReceiptSubmit(
        tx_hash="0x222", chain="base", token="USDC",
        amount=5.0, payer="0xp", payee="0xr",
    )
    errors = svc.validate_receipt(receipt, required_amount=10.0)
    assert any("amount" in e.lower() for e in errors)


@pytest.mark.asyncio
async def test_validate_receipt_accepts_valid(db_session: AsyncSession):
    """A valid receipt on a supported chain with sufficient amount should pass."""
    svc = X402PaymentService(db_session)
    receipt = X402ReceiptSubmit(
        tx_hash="0x333", chain="base", token="USDC",
        amount=10.0, payer="0xp", payee="0xr",
    )
    errors = svc.validate_receipt(receipt, required_amount=10.0)
    assert errors == []
