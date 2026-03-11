"""Credit ledger service -- accounts, balances, purchases, and transfers."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.exceptions import InsufficientCreditsError, SpendingLimitError
from src.models.account import Account
from src.models.task import Task
from src.models.transaction import Transaction, TransactionType


class CreditLedgerService:
    """Manages credit accounts, reservations, charges, and refunds."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Account management
    # ------------------------------------------------------------------

    async def get_or_create_account(self, owner_id: UUID) -> Account:
        """Get an existing account or create one with the default signup bonus."""
        stmt = select(Account).where(Account.owner_id == owner_id)
        result = await self.db.execute(stmt)
        account = result.scalars().first()

        if account:
            return account

        account = Account(
            owner_id=owner_id,
            balance=Decimal(str(settings.default_credits_bonus)),
            reserved=Decimal("0"),
            currency="CREDITS",
        )
        self.db.add(account)
        await self.db.flush()

        # Record the bonus as a transaction
        bonus_txn = Transaction(
            from_account_id=None,
            to_account_id=account.id,
            amount=Decimal(str(settings.default_credits_bonus)),
            type=TransactionType.BONUS,
            description="New account signup bonus",
        )
        self.db.add(bonus_txn)
        await self.db.commit()
        await self.db.refresh(account)
        return account

    # ------------------------------------------------------------------
    # Balance
    # ------------------------------------------------------------------

    async def get_balance(self, owner_id: UUID) -> dict:
        """Return balance, reserved, available, and currency."""
        account = await self.get_or_create_account(owner_id)
        available = account.balance - account.reserved
        return {
            "balance": float(account.balance),
            "reserved": float(account.reserved),
            "available": float(available),
            "currency": account.currency,
        }

    # ------------------------------------------------------------------
    # Purchase
    # ------------------------------------------------------------------

    async def purchase_credits(
        self, owner_id: UUID, amount: float, description: str | None = None,
    ) -> Transaction:
        """Add credits to account and create a purchase transaction."""
        account = await self.get_or_create_account(owner_id)
        account.balance += Decimal(str(amount))

        txn = Transaction(
            from_account_id=None,  # external source
            to_account_id=account.id,
            amount=Decimal(str(amount)),
            type=TransactionType.PURCHASE,
            description=description or f"Credit purchase of {amount}",
        )
        self.db.add(txn)
        await self.db.commit()
        await self.db.refresh(txn)
        return txn

    # ------------------------------------------------------------------
    # Reserve
    # ------------------------------------------------------------------

    async def check_daily_spend(self, owner_id: UUID, additional: float = 0) -> None:
        """Check if a user would exceed their daily spending limit.

        Raises SpendingLimitError if the user's daily spend + additional
        would exceed their configured limit.
        """
        from src.models.user import User

        user = await self.db.get(User, owner_id)
        limit = user.daily_spend_limit if user else None
        if not limit or limit <= 0:
            return  # No limit set

        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        account = await self.get_or_create_account(owner_id)

        spent_stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.from_account_id == account.id,
            Transaction.type == TransactionType.TASK_PAYMENT,
            Transaction.created_at >= today_start,
        )
        today_spent = float((await self.db.execute(spent_stmt)).scalar_one())

        if today_spent + additional > limit:
            raise SpendingLimitError(
                detail=f"Daily spending limit of {limit} credits would be exceeded "
                f"(spent today: {today_spent:.1f}, requested: {additional:.1f})"
            )

    async def reserve_credits(
        self, owner_id: UUID, amount: float, task_id: UUID | None = None
    ) -> None:
        """Reserve credits for an upcoming task (atomic).

        Uses SELECT FOR UPDATE to prevent race conditions where two
        concurrent requests could both pass the balance check.

        Raises InsufficientCreditsError if available balance is too low.
        """
        # Check daily spending limit before reserving
        await self.check_daily_spend(owner_id, amount)

        dec_amount = Decimal(str(amount))

        # Lock the row to prevent concurrent over-reservation
        stmt = (
            select(Account)
            .where(Account.owner_id == owner_id)
            .with_for_update()
        )
        result = await self.db.execute(stmt)
        account = result.scalars().first()

        if not account:
            account = await self.get_or_create_account(owner_id)
            # Re-lock after creation
            result = await self.db.execute(
                select(Account).where(Account.owner_id == owner_id).with_for_update()
            )
            account = result.scalars().first()

        available = account.balance - account.reserved

        if available < dec_amount:
            raise InsufficientCreditsError(
                detail=f"Available credits ({float(available)}) insufficient "
                f"for reservation of {amount}"
            )

        account.reserved += dec_amount
        await self.db.commit()

    # ------------------------------------------------------------------
    # Charge (transfer)
    # ------------------------------------------------------------------

    async def charge_credits(
        self,
        client_owner_id: UUID,
        provider_owner_id: UUID,
        amount: float,
        task_id: UUID,
    ) -> Transaction:
        """Transfer credits from client to provider, deducting the platform fee.

        - Client: balance -= amount, reserved -= amount
        - Provider: balance += amount * (1 - platform_fee_rate)
        - Platform fee recorded as a separate transaction
        """
        client_account = await self.get_or_create_account(client_owner_id)
        provider_account = await self.get_or_create_account(provider_owner_id)

        dec_amount = Decimal(str(amount))
        fee_rate = Decimal(str(settings.platform_fee_rate))
        fee = dec_amount * fee_rate
        provider_amount = dec_amount - fee

        # Debit client
        client_account.balance -= dec_amount
        client_account.reserved -= dec_amount

        # Credit provider
        provider_account.balance += provider_amount

        # Task payment transaction
        payment_txn = Transaction(
            from_account_id=client_account.id,
            to_account_id=provider_account.id,
            amount=provider_amount,
            type=TransactionType.TASK_PAYMENT,
            task_id=task_id,
            description=f"Task payment for task {task_id}",
        )
        self.db.add(payment_txn)

        # Platform fee transaction
        fee_txn = Transaction(
            from_account_id=client_account.id,
            to_account_id=None,  # platform
            amount=fee,
            type=TransactionType.PLATFORM_FEE,
            task_id=task_id,
            description=f"Platform fee ({float(fee_rate) * 100:.0f}%) for task {task_id}",
        )
        self.db.add(fee_txn)

        await self.db.commit()
        await self.db.refresh(payment_txn)
        return payment_txn

    # ------------------------------------------------------------------
    # Release
    # ------------------------------------------------------------------

    async def release_credits(
        self, owner_id: UUID, amount: float, task_id: UUID
    ) -> None:
        """Release previously reserved credits (on cancel or failure)."""
        account = await self.get_or_create_account(owner_id)
        account.reserved = max(
            Decimal("0"), account.reserved - Decimal(str(amount))
        )
        await self.db.commit()

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------

    async def get_transactions(
        self, owner_id: UUID, page: int = 1, per_page: int = 20
    ) -> tuple[list[Transaction], int]:
        """List transactions for the user's account, paginated."""
        account = await self.get_or_create_account(owner_id)

        stmt = select(Transaction).where(
            (Transaction.from_account_id == account.id)
            | (Transaction.to_account_id == account.id)
        )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        offset = (page - 1) * per_page
        stmt = stmt.offset(offset).limit(per_page).order_by(
            Transaction.created_at.desc()
        )
        result = await self.db.execute(stmt)
        transactions = list(result.scalars().all())

        return transactions, total

    # ------------------------------------------------------------------
    # Usage
    # ------------------------------------------------------------------

    async def get_usage(
        self, owner_id: UUID, period: str = "30d"
    ) -> dict:
        """Aggregate usage stats: total_spent, total_earned, tasks_created, tasks_received."""
        account = await self.get_or_create_account(owner_id)

        # Parse period
        days = int(period.rstrip("d")) if period.endswith("d") else 30
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Total spent (outgoing payments)
        spent_stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.from_account_id == account.id,
            Transaction.type == TransactionType.TASK_PAYMENT,
            Transaction.created_at >= since,
        )
        total_spent = float((await self.db.execute(spent_stmt)).scalar_one())

        # Total earned (incoming payments)
        earned_stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.to_account_id == account.id,
            Transaction.type == TransactionType.TASK_PAYMENT,
            Transaction.created_at >= since,
        )
        total_earned = float((await self.db.execute(earned_stmt)).scalar_one())

        # Tasks created (as client) -- find agents owned by user, then count tasks
        from src.models.agent import Agent

        owned_agent_ids_stmt = select(Agent.id).where(Agent.owner_id == owner_id)
        owned_ids = (await self.db.execute(owned_agent_ids_stmt)).scalars().all()

        tasks_created = 0
        tasks_received = 0
        if owned_ids:
            created_stmt = select(func.count()).where(
                Task.client_agent_id.in_(owned_ids),
                Task.created_at >= since,
            )
            tasks_created = (await self.db.execute(created_stmt)).scalar_one()

            received_stmt = select(func.count()).where(
                Task.provider_agent_id.in_(owned_ids),
                Task.created_at >= since,
            )
            tasks_received = (await self.db.execute(received_stmt)).scalar_one()

        return {
            "total_spent": total_spent,
            "total_earned": total_earned,
            "tasks_created": tasks_created,
            "tasks_received": tasks_received,
            "period": period,
        }

    # ------------------------------------------------------------------
    # Spend breakdown by agent
    # ------------------------------------------------------------------

    async def get_spend_by_agent(
        self, owner_id: UUID, period: str = "30d"
    ) -> list[dict]:
        """Break down credit spending by provider agent for the user."""
        from src.models.agent import Agent

        days = int(period.rstrip("d")) if period.endswith("d") else 30
        since = datetime.now(timezone.utc) - timedelta(days=days)

        stmt = (
            select(
                Task.provider_agent_id,
                Agent.name.label("agent_name"),
                Agent.category.label("agent_category"),
                func.count(Task.id).label("tasks_count"),
                func.coalesce(func.sum(Task.credits_charged), 0).label("total_spent"),
            )
            .join(Agent, Agent.id == Task.provider_agent_id)
            .where(
                Task.creator_user_id == owner_id,
                Task.credits_charged.is_not(None),
                Task.credits_charged > 0,
                Task.created_at >= since,
            )
            .group_by(Task.provider_agent_id, Agent.name, Agent.category)
            .order_by(func.sum(Task.credits_charged).desc())
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "agent_id": str(row.provider_agent_id),
                "agent_name": row.agent_name,
                "agent_category": row.agent_category,
                "tasks_count": row.tasks_count,
                "total_spent": float(row.total_spent),
                "avg_cost": round(float(row.total_spent) / row.tasks_count, 2)
                if row.tasks_count > 0
                else 0,
            }
            for row in rows
        ]
