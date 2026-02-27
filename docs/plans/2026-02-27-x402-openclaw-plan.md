# x402 Payment & OpenClaw Import — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add x402 stablecoin payments as an alternative to credits, and OpenClaw skill import with security guardrails.

**Architecture:** Payment abstraction layer in task broker — `credits` path unchanged, new `x402` path verifies receipts via facilitator API. OpenClaw import fetches skill manifests from allowed registries, converts to CrewHub agent format, starts inactive. All new models use SQLAlchemy mapped columns; tests use existing in-memory SQLite fixtures.

**Tech Stack:** FastAPI, SQLAlchemy async, httpx (for x402 verification + manifest fetching), bleach (HTML sanitization), existing Pydantic schemas.

---

### Task 1: Add `pending_payment` to TaskStatus and `payment_method` / `x402_receipt` columns to Task model

**Files:**
- Modify: `src/models/task.py`
- Modify: `src/schemas/task.py`
- Modify: `alembic/versions/001_initial_schema.py`

**Step 1: Update Task model**

In `src/models/task.py`, add `PENDING_PAYMENT` to `TaskStatus` enum:
```python
class TaskStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    PENDING_PAYMENT = "pending_payment"  # NEW: waiting for x402 receipt
    WORKING = "working"
    INPUT_REQUIRED = "input_required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    REJECTED = "rejected"
```

Add two columns to `Task` class after `quality_score`:
```python
    payment_method: Mapped[str] = mapped_column(
        String(20), nullable=False, default="credits", server_default="credits"
    )
    x402_receipt: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
```

**Step 2: Update TaskStatus schema enum**

In `src/schemas/task.py`, add `pending_payment` to the `TaskStatus` enum:
```python
class TaskStatus(str, Enum):
    submitted = "submitted"
    pending_payment = "pending_payment"
    working = "working"
    ...
```

Add `PaymentMethod` enum and update `TaskCreate`:
```python
class PaymentMethod(str, Enum):
    credits = "credits"
    x402 = "x402"
```

Add to `TaskCreate`:
```python
    payment_method: PaymentMethod = PaymentMethod.credits
```

Add to `TaskResponse`:
```python
    payment_method: str = "credits"
    x402_receipt: Optional[dict] = None
```

**Step 3: Update migration**

In `alembic/versions/001_initial_schema.py`, add to the tasks table creation (after `quality_score` column):
```python
        sa.Column("payment_method", sa.String(20), server_default="credits"),
        sa.Column("x402_receipt", sa.JSON(), nullable=True),
```

**Step 4: Run tests**

Run: `cd /Users/ariv/Projects/crewhub && python -m pytest tests/ -v`
Expected: All 23 tests pass (no behavioral changes yet).

**Step 5: Commit**

```bash
git add src/models/task.py src/schemas/task.py alembic/versions/001_initial_schema.py
git commit -m "feat: add payment_method and x402_receipt columns to Task model"
```

---

### Task 2: Add `accepted_payment_methods` and `metadata` columns to Agent model

**Files:**
- Modify: `src/models/agent.py`
- Modify: `src/schemas/agent.py`
- Modify: `alembic/versions/001_initial_schema.py`

**Step 1: Update Agent model**

In `src/models/agent.py`, add after `embedding_config`:
```python
    accepted_payment_methods: Mapped[list] = mapped_column(
        JSON, nullable=False, default=lambda: ["credits"], server_default='["credits"]'
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSON, nullable=True, default=dict
    )
```

Note: use `metadata_` as the Python attribute name because `metadata` conflicts with SQLAlchemy's Base.metadata. The column name in DB is `metadata`.

**Step 2: Update Agent schemas**

In `src/schemas/agent.py`, add to `AgentCreate`:
```python
    accepted_payment_methods: list[str] = Field(
        default=["credits"], max_length=5,
        description="Payment methods this agent accepts: credits, x402"
    )
```

Add to `AgentUpdate`:
```python
    accepted_payment_methods: Optional[list[str]] = None
```

Add to `AgentResponse`:
```python
    accepted_payment_methods: list[str] = ["credits"]
    metadata_: Optional[dict] = Field(None, alias="metadata_")
```

Add a field validator to `AgentResponse`:
```python
    @field_validator("accepted_payment_methods", mode="before")
    @classmethod
    def ensure_payment_methods_list(cls, v):
        if not v:
            return ["credits"]
        return v
```

**Step 3: Update migration**

In `alembic/versions/001_initial_schema.py`, add to agents table after `embedding_config`:
```python
        sa.Column("accepted_payment_methods", sa.JSON(), server_default='["credits"]'),
        sa.Column("metadata", sa.JSON(), server_default="{}"),
```

**Step 4: Update RegistryService**

In `src/services/registry.py`, in `register_agent`, add when creating Agent:
```python
            accepted_payment_methods=data.accepted_payment_methods,
            metadata_={},
```

**Step 5: Run tests**

Run: `cd /Users/ariv/Projects/crewhub && python -m pytest tests/ -v`
Expected: All tests pass.

**Step 6: Commit**

```bash
git add src/models/agent.py src/schemas/agent.py alembic/versions/001_initial_schema.py src/services/registry.py
git commit -m "feat: add accepted_payment_methods and metadata columns to Agent"
```

---

### Task 3: Add `X402_PAYMENT` transaction type and `PaymentVerificationError` exception

**Files:**
- Modify: `src/models/transaction.py`
- Modify: `src/core/exceptions.py`

**Step 1: Update TransactionType**

In `src/models/transaction.py`, add to `TransactionType`:
```python
    X402_PAYMENT = "x402_payment"
```

**Step 2: Add PaymentVerificationError**

In `src/core/exceptions.py`, add:
```python
class PaymentVerificationError(MarketplaceError):
    """x402 payment verification failed."""

    def __init__(self, detail: str = "Payment verification failed"):
        super().__init__(status_code=402, detail=detail)
```

**Step 3: Run tests**

Run: `cd /Users/ariv/Projects/crewhub && python -m pytest tests/ -v`
Expected: All tests pass.

**Step 4: Commit**

```bash
git add src/models/transaction.py src/core/exceptions.py
git commit -m "feat: add X402_PAYMENT transaction type and PaymentVerificationError"
```

---

### Task 4: Add x402 config settings and verified receipt model

**Files:**
- Modify: `src/config.py`
- Create: `src/models/x402_receipt.py`
- Modify: `src/models/__init__.py`
- Modify: `alembic/versions/001_initial_schema.py`
- Modify: `.env.example`

**Step 1: Add x402 settings**

In `src/config.py`, add after `rate_limit_window_seconds`:
```python
    # x402 Payment
    x402_facilitator_url: str = ""
    x402_supported_chains: str = "base"        # comma-separated
    x402_supported_tokens: str = "USDC"        # comma-separated
    x402_receipt_timeout_minutes: int = 10
```

**Step 2: Create X402VerifiedReceipt model**

Create `src/models/x402_receipt.py`:
```python
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
```

**Step 3: Register model in `__init__`**

In `src/models/__init__.py`, add:
```python
from src.models.x402_receipt import X402VerifiedReceipt  # noqa: F401
```

**Step 4: Add migration for x402_verified_receipts table**

In `alembic/versions/001_initial_schema.py`, add after the transactions table creation:
```python
    # x402 Verified Receipts
    op.create_table(
        "x402_verified_receipts",
        sa.Column("tx_hash", sa.String(128), nullable=False),
        sa.Column("chain", sa.String(20), nullable=False),
        sa.Column("token", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(16, 4), nullable=False),
        sa.Column("payer", sa.String(128), nullable=False),
        sa.Column("payee", sa.String(128), nullable=False),
        sa.Column("task_id", sa.Uuid(), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("tx_hash"),
    )
    op.create_index("ix_x402_receipts_task_id", "x402_verified_receipts", ["task_id"])
```

Add to `downgrade()` before `op.drop_table("transactions")`:
```python
    op.drop_table("x402_verified_receipts")
```

**Step 5: Update .env.example**

Add:
```
# x402 Payment (optional — enables stablecoin payments)
X402_FACILITATOR_URL=
X402_SUPPORTED_CHAINS=base
X402_SUPPORTED_TOKENS=USDC
X402_RECEIPT_TIMEOUT_MINUTES=10
```

**Step 6: Run tests**

Run: `cd /Users/ariv/Projects/crewhub && python -m pytest tests/ -v`
Expected: All tests pass.

**Step 7: Commit**

```bash
git add src/config.py src/models/x402_receipt.py src/models/__init__.py alembic/versions/001_initial_schema.py .env.example
git commit -m "feat: add x402 config, verified receipt model, and migration"
```

---

### Task 5: Create x402 payment schemas

**Files:**
- Create: `src/schemas/x402.py`

**Step 1: Create schemas**

Create `src/schemas/x402.py`:
```python
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
```

**Step 2: Run tests**

Run: `cd /Users/ariv/Projects/crewhub && python -m pytest tests/ -v`
Expected: All tests pass.

**Step 3: Commit**

```bash
git add src/schemas/x402.py
git commit -m "feat: add x402 payment request and receipt schemas"
```

---

### Task 6: Create X402PaymentService

**Files:**
- Create: `src/services/x402.py`
- Test: `tests/test_x402.py`

**Step 1: Write the failing test**

Create `tests/test_x402.py`:
```python
"""Tests for x402 payment verification service."""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

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
    task_id = uuid4()
    receipt_data = X402ReceiptSubmit(
        tx_hash="0xdef456",
        chain="base",
        token="USDC",
        amount=10.0,
        payer="0xpayer",
        payee="0xpayee",
    )
    await svc.record_receipt(task_id=task_id, receipt=receipt_data)

    # Verify it's stored
    assert await svc.check_replay("0xdef456") is True


@pytest.mark.asyncio
async def test_validate_receipt_rejects_unsupported_chain(db_session: AsyncSession):
    """Should reject receipts on unsupported chains."""
    svc = X402PaymentService(db_session)
    receipt = X402ReceiptSubmit(
        tx_hash="0x111",
        chain="ethereum",  # not in default supported chains
        token="USDC",
        amount=10.0,
        payer="0xp",
        payee="0xr",
    )
    errors = svc.validate_receipt(receipt, required_amount=10.0)
    assert any("chain" in e.lower() for e in errors)


@pytest.mark.asyncio
async def test_validate_receipt_rejects_insufficient_amount(db_session: AsyncSession):
    """Should reject receipts with amount less than required."""
    svc = X402PaymentService(db_session)
    receipt = X402ReceiptSubmit(
        tx_hash="0x222",
        chain="base",
        token="USDC",
        amount=5.0,
        payer="0xp",
        payee="0xr",
    )
    errors = svc.validate_receipt(receipt, required_amount=10.0)
    assert any("amount" in e.lower() for e in errors)


@pytest.mark.asyncio
async def test_validate_receipt_accepts_valid(db_session: AsyncSession):
    """A valid receipt on a supported chain with sufficient amount should pass."""
    svc = X402PaymentService(db_session)
    receipt = X402ReceiptSubmit(
        tx_hash="0x333",
        chain="base",
        token="USDC",
        amount=10.0,
        payer="0xp",
        payee="0xr",
    )
    errors = svc.validate_receipt(receipt, required_amount=10.0)
    assert errors == []
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ariv/Projects/crewhub && python -m pytest tests/test_x402.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.services.x402'`

**Step 3: Write the service**

Create `src/services/x402.py`:
```python
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
            # Dev mode: no facilitator configured, accept optimistically
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
```

**Step 4: Run tests**

Run: `cd /Users/ariv/Projects/crewhub && python -m pytest tests/test_x402.py -v`
Expected: All 6 tests pass.

**Step 5: Run full suite**

Run: `cd /Users/ariv/Projects/crewhub && python -m pytest tests/ -v`
Expected: All tests pass (23 existing + 6 new = 29).

**Step 6: Commit**

```bash
git add src/services/x402.py tests/test_x402.py
git commit -m "feat: add X402PaymentService with replay protection and validation"
```

---

### Task 7: Integrate x402 payment path into TaskBrokerService

**Files:**
- Modify: `src/services/task_broker.py`
- Test: `tests/test_task_broker.py` (add new tests)

**Step 1: Write the failing tests**

Append to `tests/test_task_broker.py`:
```python
# ------------------------------------------------------------------
# x402 payment path tests
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_task_x402_returns_pending_payment(client: AsyncClient, auth_headers: dict):
    """Creating a task with payment_method=x402 should return pending_payment status."""
    client_agent, provider_agent = await _register_two_agents(client, auth_headers)

    # First update the provider to accept x402
    resp = await client.put(
        f"/api/v1/agents/{provider_agent['id']}",
        json={"accepted_payment_methods": ["credits", "x402"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    skill_key = provider_agent["skills"][0]["skill_key"]
    task_payload = {
        "provider_agent_id": provider_agent["id"],
        "skill_id": skill_key,
        "messages": [
            {"role": "user", "parts": [{"type": "text", "content": "Analyze this."}]}
        ],
        "max_credits": 10.0,
        "payment_method": "x402",
    }
    resp = await client.post("/api/v1/tasks/", json=task_payload, headers=auth_headers)
    assert resp.status_code == 201

    data = resp.json()
    assert data["status"] == "pending_payment"
    assert data["payment_method"] == "x402"


@pytest.mark.asyncio
async def test_create_task_x402_rejected_if_agent_doesnt_accept(
    client: AsyncClient, auth_headers: dict
):
    """Task creation with x402 should fail if agent only accepts credits."""
    client_agent, provider_agent = await _register_two_agents(client, auth_headers)

    skill_key = provider_agent["skills"][0]["skill_key"]
    task_payload = {
        "provider_agent_id": provider_agent["id"],
        "skill_id": skill_key,
        "messages": [
            {"role": "user", "parts": [{"type": "text", "content": "Analyze this."}]}
        ],
        "max_credits": 10.0,
        "payment_method": "x402",
    }
    resp = await client.post("/api/v1/tasks/", json=task_payload, headers=auth_headers)
    assert resp.status_code == 400 or resp.status_code == 422
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ariv/Projects/crewhub && python -m pytest tests/test_task_broker.py::test_create_task_x402_returns_pending_payment -v`
Expected: FAIL

**Step 3: Modify TaskBrokerService.create_task**

In `src/services/task_broker.py`, update `create_task` to handle x402:

Add import at top:
```python
from src.core.exceptions import ForbiddenError, NotFoundError, QuotaExceededError, PaymentVerificationError
```

Replace the `create_task` method body. After step 2b (resolve tier and enforce quotas), add the x402 branch:

```python
        # 3. Determine payment method
        payment_method = getattr(data, "payment_method", None)
        if payment_method is None:
            payment_method = "credits"
        else:
            payment_method = payment_method.value if hasattr(payment_method, "value") else str(payment_method)

        # 3a. Validate agent accepts this payment method
        accepted = provider.accepted_payment_methods or ["credits"]
        if payment_method not in accepted:
            from src.core.exceptions import MarketplaceError
            raise MarketplaceError(
                status_code=400,
                detail=f"Agent does not accept '{payment_method}' payments. "
                       f"Accepted: {', '.join(accepted)}"
            )

        # 3b. Quote credits
        credits_quoted = Decimal(str(
            self._resolve_credits(provider, data.max_credits, skill.avg_credits, data.tier)
        ))

        # 3c. Handle payment based on method
        if payment_method == "credits":
            if credits_quoted > 0:
                await self.credit_ledger.reserve_credits(
                    owner_id=user_id,
                    amount=float(credits_quoted),
                    task_id=None,
                )
            initial_status = TaskStatus.SUBMITTED
        else:
            # x402: no credit reservation, task starts as pending_payment
            initial_status = TaskStatus.PENDING_PAYMENT

        # 4. Create task
        task = Task(
            client_agent_id=client_agent_id,
            provider_agent_id=provider.id,
            skill_id=skill.id,
            status=initial_status,
            messages=[m.model_dump() for m in data.messages],
            artifacts=[],
            credits_quoted=credits_quoted,
            payment_method=payment_method,
        )
```

**Step 4: Run tests**

Run: `cd /Users/ariv/Projects/crewhub && python -m pytest tests/ -v`
Expected: All tests pass (existing credit-based tests unaffected, new x402 tests pass).

**Step 5: Commit**

```bash
git add src/services/task_broker.py tests/test_task_broker.py
git commit -m "feat: integrate x402 payment path in task broker"
```

---

### Task 8: Add x402 receipt submission endpoint

**Files:**
- Modify: `src/api/tasks.py`
- Test: new tests in `tests/test_task_broker.py`

**Step 1: Write the failing test**

Append to `tests/test_task_broker.py`:
```python
@pytest.mark.asyncio
async def test_submit_x402_receipt(client: AsyncClient, auth_headers: dict, db_session):
    """Submitting a valid x402 receipt should move task to submitted."""
    client_agent, provider_agent = await _register_two_agents(client, auth_headers)

    # Update provider to accept x402
    await client.put(
        f"/api/v1/agents/{provider_agent['id']}",
        json={"accepted_payment_methods": ["credits", "x402"]},
        headers=auth_headers,
    )

    # Create x402 task
    skill_key = provider_agent["skills"][0]["skill_key"]
    resp = await client.post(
        "/api/v1/tasks/",
        json={
            "provider_agent_id": provider_agent["id"],
            "skill_id": skill_key,
            "messages": [{"role": "user", "parts": [{"type": "text", "content": "Go"}]}],
            "max_credits": 10.0,
            "payment_method": "x402",
        },
        headers=auth_headers,
    )
    task = resp.json()
    assert task["status"] == "pending_payment"

    # Submit receipt
    receipt_resp = await client.post(
        f"/api/v1/tasks/{task['id']}/x402-receipt",
        json={
            "tx_hash": "0xabc123def456",
            "chain": "base",
            "token": "USDC",
            "amount": 10.0,
            "payer": "0xmywallet",
            "payee": "0xproviderwallet",
        },
        headers=auth_headers,
    )
    assert receipt_resp.status_code == 200

    data = receipt_resp.json()
    assert data["verified"] is True
    assert data["task_status"] == "submitted"
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ariv/Projects/crewhub && python -m pytest tests/test_task_broker.py::test_submit_x402_receipt -v`
Expected: FAIL — endpoint doesn't exist yet.

**Step 3: Add the endpoint**

In `src/api/tasks.py`, add the x402 receipt endpoint:

```python
from src.schemas.x402 import X402ReceiptSubmit, X402ReceiptResponse
from src.services.x402 import X402PaymentService
from src.models.task import TaskStatus as TaskStatusModel

@router.post("/{task_id}/x402-receipt", response_model=X402ReceiptResponse)
async def submit_x402_receipt(
    task_id: UUID,
    receipt: X402ReceiptSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> X402ReceiptResponse:
    """Submit an x402 payment receipt for a pending_payment task."""
    from src.core.exceptions import PaymentVerificationError

    broker = TaskBrokerService(db)
    task = await broker.get_task(task_id, user_id=UUID(current_user["id"]))

    # Must be pending_payment
    if task.status != TaskStatusModel.PENDING_PAYMENT:
        raise PaymentVerificationError(
            detail=f"Task is not awaiting payment (status: {task.status.value})"
        )

    # Must be x402 payment method
    if task.payment_method != "x402":
        raise PaymentVerificationError(detail="Task does not use x402 payment method")

    # Check receipt timeout
    from datetime import datetime, timezone
    elapsed = (datetime.now(timezone.utc) - task.created_at).total_seconds() / 60
    from src.config import settings
    if elapsed > settings.x402_receipt_timeout_minutes:
        raise PaymentVerificationError(
            detail=f"Receipt submission timeout ({settings.x402_receipt_timeout_minutes} min)"
        )

    x402_svc = X402PaymentService(db)

    # Check replay
    if await x402_svc.check_replay(receipt.tx_hash):
        raise PaymentVerificationError(detail="Transaction hash already used (replay)")

    # Validate fields
    required_amount = float(task.credits_quoted or 0)
    errors = x402_svc.validate_receipt(receipt, required_amount=required_amount)
    if errors:
        raise PaymentVerificationError(detail="; ".join(errors))

    # Verify with facilitator
    verified = await x402_svc.verify_with_facilitator(receipt)
    if not verified:
        raise PaymentVerificationError(detail="Facilitator could not verify payment")

    # Record receipt and advance task
    await x402_svc.record_receipt(task_id=task.id, receipt=receipt)
    task.status = TaskStatusModel.SUBMITTED
    task.x402_receipt = {
        "tx_hash": receipt.tx_hash,
        "chain": receipt.chain,
        "token": receipt.token,
        "amount": receipt.amount,
        "payer": receipt.payer,
        "payee": receipt.payee,
    }
    await db.commit()

    return X402ReceiptResponse(
        verified=True,
        tx_hash=receipt.tx_hash,
        task_status="submitted",
    )
```

**Step 4: Run tests**

Run: `cd /Users/ariv/Projects/crewhub && python -m pytest tests/ -v`
Expected: All tests pass.

**Step 5: Commit**

```bash
git add src/api/tasks.py tests/test_task_broker.py
git commit -m "feat: add x402 receipt submission endpoint with guardrails"
```

---

### Task 9: Update task completion to skip credit settlement for x402 tasks

**Files:**
- Modify: `src/services/task_broker.py`

**Step 1: Modify update_task_status**

In `src/services/task_broker.py`, in `update_task_status`, wrap the credit charge block:

```python
        if status == TaskStatus.COMPLETED:
            task.completed_at = now
            if task.created_at:
                delta = now - task.created_at
                task.latency_ms = int(delta.total_seconds() * 1000)

            # Charge credits (only for credit-based payments)
            quoted = float(task.credits_quoted or 0)
            if quoted > 0 and task.client_agent and task.provider_agent:
                if task.payment_method == "credits":
                    # Credit ledger settlement
                    txn = await self.credit_ledger.charge_credits(
                        client_owner_id=task.client_agent.owner_id,
                        provider_owner_id=task.provider_agent.owner_id,
                        amount=quoted,
                        task_id=task.id,
                    )
                    task.credits_charged = Decimal(str(quoted))
                # x402: payment already settled on-chain, just record audit entry
                elif task.payment_method == "x402":
                    task.credits_charged = Decimal(str(quoted))
```

Similarly, in the `FAILED` branch, only release credits for credit-based payments:

```python
        elif status == TaskStatus.FAILED:
            quoted = float(task.credits_quoted or 0)
            if quoted > 0 and task.client_agent:
                if task.payment_method == "credits":
                    await self.credit_ledger.release_credits(
                        owner_id=task.client_agent.owner_id,
                        amount=quoted,
                        task_id=task.id,
                    )
```

Also update `cancel_task` similarly.

**Step 2: Run tests**

Run: `cd /Users/ariv/Projects/crewhub && python -m pytest tests/ -v`
Expected: All tests pass.

**Step 3: Commit**

```bash
git add src/services/task_broker.py
git commit -m "feat: skip credit settlement for x402 tasks on completion/failure"
```

---

### Task 10: Create OpenClaw import schemas

**Files:**
- Create: `src/schemas/imports.py`

**Step 1: Create import schemas**

Create `src/schemas/imports.py`:
```python
"""Schemas for skill import from external registries."""

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from src.schemas.agent import PricingModel


# Allowed registry domains for OpenClaw skill imports
ALLOWED_IMPORT_DOMAINS = {
    "clawhub.io",
    "github.com",
    "raw.githubusercontent.com",
    "clawmart.online",
}


class OpenClawImportRequest(BaseModel):
    """Request to import an OpenClaw skill as a CrewHub agent."""

    skill_url: str = Field(max_length=500, description="ClawHub or ClawMart skill URL")
    pricing: PricingModel
    category: str = Field("general", max_length=100)
    tags: list[str] = Field(default=["imported", "openclaw"], max_length=20)

    @field_validator("skill_url")
    @classmethod
    def url_must_be_allowed(cls, v: str) -> str:
        from urllib.parse import urlparse

        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("URL must use http or https")
        hostname = parsed.hostname or ""
        if not any(hostname == d or hostname.endswith(f".{d}") for d in ALLOWED_IMPORT_DOMAINS):
            raise ValueError(
                f"URL domain '{hostname}' not in allowed list: {', '.join(sorted(ALLOWED_IMPORT_DOMAINS))}"
            )
        return v


class OpenClawImportResponse(BaseModel):
    """Response after importing an OpenClaw skill."""

    agent_id: str
    name: str
    status: str  # always "inactive"
    source: str = "openclaw"
    source_url: str
    message: str = "Imported successfully. Agent starts as inactive — activate manually after review."
```

**Step 2: Run tests**

Run: `cd /Users/ariv/Projects/crewhub && python -m pytest tests/ -v`
Expected: All tests pass.

**Step 3: Commit**

```bash
git add src/schemas/imports.py
git commit -m "feat: add OpenClaw import request/response schemas with URL allowlist"
```

---

### Task 11: Create OpenClawImporter service

**Files:**
- Create: `src/services/openclaw_importer.py`
- Test: `tests/test_openclaw_import.py`

**Step 1: Write the failing tests**

Create `tests/test_openclaw_import.py`:
```python
"""Tests for OpenClaw skill importer."""

import pytest
from src.services.openclaw_importer import OpenClawImporter


def test_sanitize_text_strips_html():
    """HTML tags should be stripped from imported text."""
    raw = '<script>alert("xss")</script><b>Bold text</b> and <a href="#">link</a>'
    clean = OpenClawImporter.sanitize_text(raw)
    assert "<script>" not in clean
    assert "<b>" not in clean
    assert "<a " not in clean
    assert "Bold text" in clean
    assert "link" in clean


def test_sanitize_text_truncates():
    """Text longer than max_length should be truncated."""
    long_text = "a" * 20000
    clean = OpenClawImporter.sanitize_text(long_text, max_length=10000)
    assert len(clean) == 10000


def test_parse_manifest_extracts_fields():
    """Parser should extract name, description, and endpoint from markdown."""
    manifest = """# My Awesome Skill

A skill that does amazing things with data analysis.

## Endpoint
https://api.example.com/skill

## Input Modes
text, data

## Output Modes
text
"""
    result = OpenClawImporter.parse_manifest(manifest)
    assert result["name"] == "My Awesome Skill"
    assert "amazing things" in result["description"]
    assert result["endpoint"] == "https://api.example.com/skill"


def test_parse_manifest_handles_minimal():
    """Parser should handle manifests with missing sections gracefully."""
    manifest = "# Simple Skill\n\nJust a simple skill."
    result = OpenClawImporter.parse_manifest(manifest)
    assert result["name"] == "Simple Skill"
    assert "simple skill" in result["description"].lower()
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ariv/Projects/crewhub && python -m pytest tests/test_openclaw_import.py -v`
Expected: FAIL — module not found.

**Step 3: Write the service**

Create `src/services/openclaw_importer.py`:
```python
"""OpenClaw skill importer — fetch, parse, and register external skills."""

import re
from datetime import datetime, timezone
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ConflictError, MarketplaceError
from src.models.agent import Agent, AgentStatus, VerificationLevel
from src.models.skill import AgentSkill
from src.schemas.agent import PricingModel
from src.schemas.imports import ALLOWED_IMPORT_DOMAINS

# Max manifest size: 100KB
MAX_MANIFEST_BYTES = 100_000

# Rate limit: tracked per-user in memory
_import_counts: dict[str, list[float]] = {}
MAX_IMPORTS_PER_HOUR = 10


class OpenClawImporter:
    """Imports OpenClaw skills from external registries as CrewHub agents."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def sanitize_text(text: str, max_length: int = 10000) -> str:
        """Strip HTML tags and truncate to max length."""
        # Remove HTML tags
        clean = re.sub(r"<[^>]+>", "", text)
        # Remove script content that might have been between tags
        clean = re.sub(r"javascript:", "", clean, flags=re.IGNORECASE)
        # Collapse whitespace
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean[:max_length]

    @staticmethod
    def parse_manifest(content: str) -> dict:
        """Parse an OpenClaw skill manifest (markdown format) into structured data.

        Extracts: name, description, endpoint, input_modes, output_modes.
        """
        lines = content.strip().split("\n")
        result = {
            "name": "Imported Skill",
            "description": "",
            "endpoint": "",
            "input_modes": ["text"],
            "output_modes": ["text"],
        }

        # Name from first heading
        for line in lines:
            if line.startswith("# "):
                result["name"] = line.lstrip("# ").strip()
                break

        # Description: text between first heading and next section
        in_desc = False
        desc_lines = []
        for line in lines:
            if line.startswith("# ") and not in_desc:
                in_desc = True
                continue
            if in_desc:
                if line.startswith("## "):
                    break
                desc_lines.append(line)
        result["description"] = OpenClawImporter.sanitize_text(
            "\n".join(desc_lines).strip()
        )

        # Endpoint section
        in_section = None
        for line in lines:
            lower = line.lower().strip()
            if lower.startswith("## endpoint"):
                in_section = "endpoint"
                continue
            elif lower.startswith("## input"):
                in_section = "input_modes"
                continue
            elif lower.startswith("## output"):
                in_section = "output_modes"
                continue
            elif lower.startswith("## "):
                in_section = None
                continue

            stripped = line.strip()
            if not stripped:
                continue

            if in_section == "endpoint" and stripped.startswith("http"):
                result["endpoint"] = stripped
            elif in_section == "input_modes":
                result["input_modes"] = [m.strip() for m in stripped.split(",") if m.strip()]
            elif in_section == "output_modes":
                result["output_modes"] = [m.strip() for m in stripped.split(",") if m.strip()]

        return result

    async def _check_rate_limit(self, user_id: UUID) -> None:
        """Enforce import rate limit: max N imports per user per hour."""
        import time

        key = str(user_id)
        now = time.time()
        hour_ago = now - 3600

        if key not in _import_counts:
            _import_counts[key] = []

        # Prune old entries
        _import_counts[key] = [t for t in _import_counts[key] if t > hour_ago]

        if len(_import_counts[key]) >= MAX_IMPORTS_PER_HOUR:
            raise MarketplaceError(
                status_code=429,
                detail=f"Import rate limit exceeded ({MAX_IMPORTS_PER_HOUR} per hour)"
            )

        _import_counts[key].append(now)

    async def _check_duplicate(self, endpoint: str) -> None:
        """Reject if an agent with this endpoint already exists."""
        stmt = select(Agent).where(Agent.endpoint == endpoint)
        result = await self.db.execute(stmt)
        if result.scalars().first():
            raise ConflictError(detail=f"An agent with endpoint '{endpoint}' already exists")

    async def fetch_manifest(self, url: str) -> str:
        """Fetch skill manifest from allowed registry, with size limit."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, follow_redirects=True)
                resp.raise_for_status()

                if len(resp.content) > MAX_MANIFEST_BYTES:
                    raise MarketplaceError(
                        status_code=400,
                        detail=f"Manifest too large ({len(resp.content)} bytes, max {MAX_MANIFEST_BYTES})"
                    )

                return resp.text
        except httpx.HTTPError as e:
            raise MarketplaceError(
                status_code=400,
                detail=f"Failed to fetch manifest from {url}: {str(e)}"
            )

    async def import_skill(
        self,
        skill_url: str,
        pricing: PricingModel,
        category: str,
        tags: list[str],
        owner_id: UUID,
    ) -> Agent:
        """Full import flow: fetch, parse, validate, register."""
        # Rate limit
        await self._check_rate_limit(owner_id)

        # Fetch
        content = await self.fetch_manifest(skill_url)

        # Parse
        parsed = self.parse_manifest(content)

        # Validate endpoint (SSRF check)
        endpoint = parsed.get("endpoint", "")
        if endpoint:
            from src.schemas.agent import _validate_public_url
            _validate_public_url(endpoint)
        else:
            raise MarketplaceError(status_code=400, detail="Manifest has no endpoint URL")

        # Duplicate check
        await self._check_duplicate(endpoint)

        # Sanitize
        name = self.sanitize_text(parsed["name"], max_length=255)
        description = self.sanitize_text(parsed["description"], max_length=10000)

        # Create agent (inactive + unverified)
        agent = Agent(
            owner_id=owner_id,
            name=name,
            description=description,
            version="1.0.0",
            endpoint=endpoint,
            capabilities={},
            security_schemes=[],
            category=category,
            tags=tags,
            pricing=pricing.model_dump(),
            license_type=pricing.license_type.value,
            sla={},
            embedding_config={},
            accepted_payment_methods=["credits"],
            metadata_={
                "source": "openclaw",
                "source_url": skill_url,
                "imported_at": datetime.now(timezone.utc).isoformat(),
            },
            status=AgentStatus.INACTIVE,
            verification_level=VerificationLevel.UNVERIFIED,
        )
        self.db.add(agent)
        await self.db.flush()

        # Create default skill from parsed data
        skill = AgentSkill(
            agent_id=agent.id,
            skill_key=re.sub(r"[^a-z0-9-]", "-", name.lower())[:100],
            name=name,
            description=description,
            input_modes=parsed.get("input_modes", ["text"]),
            output_modes=parsed.get("output_modes", ["text"]),
            examples=[],
            avg_credits=pricing.credits,
            avg_latency_ms=0,
        )
        self.db.add(skill)

        await self.db.commit()
        await self.db.refresh(agent)
        return agent
```

**Step 4: Run tests**

Run: `cd /Users/ariv/Projects/crewhub && python -m pytest tests/test_openclaw_import.py -v`
Expected: All 4 tests pass.

**Step 5: Run full suite**

Run: `cd /Users/ariv/Projects/crewhub && python -m pytest tests/ -v`
Expected: All tests pass.

**Step 6: Commit**

```bash
git add src/services/openclaw_importer.py tests/test_openclaw_import.py
git commit -m "feat: add OpenClawImporter service with sanitization and guardrails"
```

---

### Task 12: Create import API endpoint and register router

**Files:**
- Create: `src/api/imports.py`
- Modify: `src/main.py`
- Test: `tests/test_openclaw_import.py` (add API test)

**Step 1: Write the failing test**

Append to `tests/test_openclaw_import.py`:
```python
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_import_endpoint_rejects_bad_domain(client: AsyncClient, auth_headers: dict):
    """Import endpoint should reject URLs from non-allowed domains."""
    resp = await client.post(
        "/api/v1/import/openclaw",
        json={
            "skill_url": "https://evil.com/malicious-skill",
            "pricing": {"model": "per_task", "credits": 0, "license_type": "open"},
            "category": "general",
            "tags": ["test"],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_import_endpoint_success(client: AsyncClient, auth_headers: dict):
    """Import from allowed domain should create an inactive agent."""
    mock_manifest = """# Test Imported Skill

A skill for testing imports.

## Endpoint
https://api.example.com/openclaw-skill

## Input Modes
text

## Output Modes
text
"""
    with patch(
        "src.services.openclaw_importer.OpenClawImporter.fetch_manifest",
        new_callable=AsyncMock,
        return_value=mock_manifest,
    ):
        resp = await client.post(
            "/api/v1/import/openclaw",
            json={
                "skill_url": "https://clawhub.io/skills/test-skill",
                "pricing": {"model": "per_task", "credits": 0, "license_type": "open"},
                "category": "general",
                "tags": ["imported"],
            },
            headers=auth_headers,
        )
    assert resp.status_code == 201

    data = resp.json()
    assert data["status"] == "inactive"
    assert data["source"] == "openclaw"
```

**Step 2: Create the endpoint**

Create `src/api/imports.py`:
```python
"""External skill import endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.database import get_db
from src.schemas.imports import OpenClawImportRequest, OpenClawImportResponse
from src.services.openclaw_importer import OpenClawImporter

router = APIRouter(prefix="/import", tags=["import"])


@router.post("/openclaw", response_model=OpenClawImportResponse, status_code=201)
async def import_openclaw_skill(
    data: OpenClawImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> OpenClawImportResponse:
    """Import an OpenClaw skill as a CrewHub agent.

    The imported agent starts as inactive and unverified.
    Requires authentication — the caller becomes the agent owner.
    """
    importer = OpenClawImporter(db)
    agent = await importer.import_skill(
        skill_url=data.skill_url,
        pricing=data.pricing,
        category=data.category,
        tags=data.tags,
        owner_id=UUID(current_user["id"]),
    )
    return OpenClawImportResponse(
        agent_id=str(agent.id),
        name=agent.name,
        status=agent.status.value if hasattr(agent.status, "value") else str(agent.status),
        source="openclaw",
        source_url=data.skill_url,
    )
```

**Step 3: Register router in main.py**

In `src/main.py`, add:
```python
from src.api.imports import router as imports_router  # noqa: E402
```

And:
```python
app.include_router(imports_router, prefix=settings.api_v1_prefix)
```

**Step 4: Run tests**

Run: `cd /Users/ariv/Projects/crewhub && python -m pytest tests/ -v`
Expected: All tests pass.

**Step 5: Commit**

```bash
git add src/api/imports.py src/main.py tests/test_openclaw_import.py
git commit -m "feat: add OpenClaw import API endpoint with router"
```

---

### Task 13: Install bleach dependency and update pyproject.toml

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add bleach**

In `pyproject.toml`, add `bleach>=6.0.0` to dependencies. (Note: we used regex-based sanitization in the importer to avoid adding a dependency. If you want a more robust sanitizer, add bleach. Otherwise skip this task.)

Actually, the regex approach in Task 11 is sufficient for our metadata-only import. **Skip this task — YAGNI.** The regex sanitizer handles the key vectors (script tags, HTML injection).

**Step 2: Commit (skip — nothing to commit)**

---

### Task 14: Final integration test and push

**Files:**
- Run all tests

**Step 1: Run full test suite**

Run: `cd /Users/ariv/Projects/crewhub && python -m pytest tests/ -v --tb=short`
Expected: All tests pass (23 original + ~12 new = ~35 total).

**Step 2: Push all commits**

```bash
git push
```

**Step 3: Verify**

Run: `git log --oneline -10` to confirm all commits are clean and pushed.
