"""Developer payout service — Stripe Connect Express accounts and withdrawals."""

import logging
import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.account import Account
from src.models.payout import PayoutRequest, PayoutStatus
from src.models.task import Task
from src.models.transaction import Transaction, TransactionType
from src.models.user import User

logger = logging.getLogger(__name__)


class PayoutService:
    """Manages Stripe Connect accounts and developer payout requests."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_stripe(self):
        import stripe
        stripe.api_key = settings.stripe_secret_key
        return stripe

    # ------------------------------------------------------------------
    # Connect account management
    # ------------------------------------------------------------------

    async def create_connect_account(self, user_id: UUID) -> str:
        """Create a Stripe Express account and return the onboarding URL."""
        stripe = self._get_stripe()
        user = await self.db.get(User, user_id)
        if not user:
            raise ValueError("User not found")

        if user.stripe_connect_account_id:
            # Already has an account — return a new onboarding link
            account_link = stripe.AccountLink.create(
                account=user.stripe_connect_account_id,
                refresh_url=f"{settings.frontend_url}/dashboard/payouts?connect=refresh",
                return_url=f"{settings.frontend_url}/dashboard/payouts?connect=success",
                type="account_onboarding",
            )
            return account_link.url

        # Create new Express account
        account = stripe.Account.create(
            type="express",
            email=user.email,
            metadata={"crewhub_user_id": str(user.id)},
            capabilities={
                "transfers": {"requested": True},
            },
        )

        user.stripe_connect_account_id = account.id
        await self.db.commit()

        # Generate onboarding link
        account_link = stripe.AccountLink.create(
            account=account.id,
            refresh_url=f"{settings.frontend_url}/dashboard/payouts?connect=refresh",
            return_url=f"{settings.frontend_url}/dashboard/payouts?connect=success",
            type="account_onboarding",
        )
        logger.info("Created Connect account %s for user %s", account.id, user_id)
        return account_link.url

    async def check_connect_status(self, user_id: UUID) -> dict:
        """Check and sync the Connect account status from Stripe."""
        user = await self.db.get(User, user_id)
        if not user or not user.stripe_connect_account_id:
            return {
                "connected": False,
                "onboarded": False,
                "payouts_enabled": False,
                "account_id": None,
            }

        stripe = self._get_stripe()
        account = stripe.Account.retrieve(user.stripe_connect_account_id)

        user.stripe_connect_onboarded = account.details_submitted
        user.stripe_connect_payouts_enabled = account.payouts_enabled
        await self.db.commit()

        return {
            "connected": True,
            "onboarded": account.details_submitted,
            "payouts_enabled": account.payouts_enabled,
            "account_id": user.stripe_connect_account_id,
        }

    # ------------------------------------------------------------------
    # Withdrawable balance
    # ------------------------------------------------------------------

    async def get_withdrawable_balance(self, user_id: UUID) -> dict:
        """Calculate withdrawable and pending-clearance credits.

        Only agent earnings (TASK_PAYMENT transactions) are withdrawable.
        BONUS (signup, admin grants) and PURCHASE (Stripe buys) are excluded
        because the queries below filter on TransactionType.TASK_PAYMENT joined
        on Task.completed_at — credits without a backing completed task can
        never appear in the withdrawal balance.

        Withdrawable = earned credits from tasks completed > 7 days ago
                       minus credits already paid out.
        Pending = earned credits from tasks completed < 7 days ago.
        """
        from src.services.credit_ledger import CreditLedgerService
        ledger = CreditLedgerService(self.db)
        account = await ledger.get_or_create_account(user_id)

        clearance_cutoff = datetime.now(timezone.utc) - timedelta(
            days=settings.payout_clearance_days
        )

        # Total earned from cleared tasks (completed > 7 days ago)
        cleared_stmt = (
            select(func.coalesce(func.sum(Transaction.amount), 0))
            .join(Task, Task.id == Transaction.task_id)
            .where(
                Transaction.to_account_id == account.id,
                Transaction.type == TransactionType.TASK_PAYMENT,
                Task.completed_at <= clearance_cutoff,
            )
        )
        total_cleared = float((await self.db.execute(cleared_stmt)).scalar_one())

        # Total earned from uncleared tasks (completed < 7 days ago)
        uncleared_stmt = (
            select(func.coalesce(func.sum(Transaction.amount), 0))
            .join(Task, Task.id == Transaction.task_id)
            .where(
                Transaction.to_account_id == account.id,
                Transaction.type == TransactionType.TASK_PAYMENT,
                Task.completed_at > clearance_cutoff,
            )
        )
        pending_clearance = float((await self.db.execute(uncleared_stmt)).scalar_one())

        # Total already paid out
        paid_out_stmt = select(
            func.coalesce(func.sum(Transaction.amount), 0)
        ).where(
            Transaction.from_account_id == account.id,
            Transaction.type == TransactionType.PAYOUT,
        )
        total_paid_out = float((await self.db.execute(paid_out_stmt)).scalar_one())

        # Total earned (all time)
        total_earned_stmt = select(
            func.coalesce(func.sum(Transaction.amount), 0)
        ).where(
            Transaction.to_account_id == account.id,
            Transaction.type == TransactionType.TASK_PAYMENT,
        )
        total_earned = float((await self.db.execute(total_earned_stmt)).scalar_one())

        withdrawable = max(0.0, total_cleared - total_paid_out)
        rate = settings.credit_to_usd_rate

        return {
            "withdrawable_credits": withdrawable,
            "withdrawable_usd_cents": int(withdrawable * rate * 100),
            "pending_clearance_credits": pending_clearance,
            "total_earned_credits": total_earned,
            "total_paid_out_credits": total_paid_out,
            "minimum_payout_credits": settings.payout_minimum_credits,
            "credit_to_usd_rate": rate,
        }

    # ------------------------------------------------------------------
    # Request payout
    # ------------------------------------------------------------------

    async def request_payout(self, user_id: UUID, amount_credits: float) -> PayoutRequest:
        """Request a payout — deduct credits and create a Stripe Transfer.

        Uses SELECT FOR UPDATE on Account to prevent double-withdrawal.
        On Stripe error, refunds credits atomically.
        """
        stripe = self._get_stripe()

        user = await self.db.get(User, user_id)
        if not user:
            raise ValueError("User not found")
        if not user.stripe_connect_account_id or not user.stripe_connect_onboarded:
            raise ValueError("Stripe Connect account not set up")
        if not user.stripe_connect_payouts_enabled:
            raise ValueError("Stripe Connect payouts not enabled — complete onboarding")

        if amount_credits < settings.payout_minimum_credits:
            raise ValueError(
                f"Minimum payout is {settings.payout_minimum_credits} credits "
                f"(${settings.payout_minimum_credits * settings.credit_to_usd_rate:.2f})"
            )

        # Check withdrawable balance
        balance_info = await self.get_withdrawable_balance(user_id)
        if amount_credits > balance_info["withdrawable_credits"]:
            raise ValueError(
                f"Requested {amount_credits} credits but only "
                f"{balance_info['withdrawable_credits']:.2f} are withdrawable"
            )

        # Calculate USD amounts
        rate = settings.credit_to_usd_rate
        gross_usd = amount_credits * rate
        gross_usd_cents = int(round(gross_usd * 100))
        stripe_fee_cents = int(math.ceil(gross_usd * 0.0025 * 100 + 25))  # 0.25% + $0.25
        net_usd_cents = gross_usd_cents - stripe_fee_cents

        if net_usd_cents <= 0:
            raise ValueError("Payout amount too small after fees")

        # Atomic balance deduction with row lock
        dec_amount = Decimal(str(amount_credits))

        stmt = (
            select(Account)
            .where(Account.owner_id == user_id)
            .with_for_update()
        )
        result = await self.db.execute(stmt)
        account = result.scalars().first()
        if not account:
            raise ValueError("No credit account found")

        available = account.balance - account.reserved
        if available < dec_amount:
            raise ValueError(
                f"Insufficient available balance ({float(available):.2f} credits)"
            )

        # Deduct credits
        account.balance -= dec_amount

        # Record payout transaction
        txn = Transaction(
            from_account_id=account.id,
            to_account_id=None,  # external (bank)
            amount=dec_amount,
            type=TransactionType.PAYOUT,
            description=f"Payout of {amount_credits} credits (${gross_usd:.2f} gross)",
        )
        self.db.add(txn)

        # Create payout request record
        payout = PayoutRequest(
            user_id=user_id,
            amount_credits=dec_amount,
            amount_usd_cents=net_usd_cents,
            stripe_fee_cents=stripe_fee_cents,
            status=PayoutStatus.PROCESSING,
        )
        self.db.add(payout)
        await self.db.flush()

        # Create Stripe Transfer
        try:
            transfer = stripe.Transfer.create(
                amount=net_usd_cents,
                currency="usd",
                destination=user.stripe_connect_account_id,
                metadata={
                    "crewhub_payout_id": str(payout.id),
                    "crewhub_user_id": str(user_id),
                    "credits": str(amount_credits),
                },
            )
            payout.stripe_transfer_id = transfer.id
            await self.db.commit()
            logger.info(
                "Payout %s created: %d credits → $%.2f (transfer %s)",
                payout.id, amount_credits, net_usd_cents / 100, transfer.id,
            )
            return payout

        except Exception as e:
            # Refund credits on Stripe failure
            account.balance += dec_amount
            payout.status = PayoutStatus.FAILED
            payout.failure_reason = str(e)[:500]
            await self.db.commit()
            logger.error("Payout %s failed (Stripe error): %s", payout.id, e)
            raise ValueError(f"Stripe transfer failed: {e}")

    # ------------------------------------------------------------------
    # Payout history
    # ------------------------------------------------------------------

    async def get_payout_history(
        self, user_id: UUID, page: int = 1, per_page: int = 20
    ) -> tuple[list[PayoutRequest], int]:
        """List payout requests for a user, paginated."""
        count_stmt = select(func.count()).where(PayoutRequest.user_id == user_id)
        total = (await self.db.execute(count_stmt)).scalar_one()

        offset = (page - 1) * per_page
        stmt = (
            select(PayoutRequest)
            .where(PayoutRequest.user_id == user_id)
            .order_by(PayoutRequest.requested_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        result = await self.db.execute(stmt)
        payouts = list(result.scalars().all())

        return payouts, total

    # ------------------------------------------------------------------
    # Webhook handler
    # ------------------------------------------------------------------

    async def handle_transfer_event(self, event_type: str, transfer: dict) -> None:
        """Handle transfer.paid / transfer.failed webhook events."""
        transfer_id = transfer.get("id")
        if not transfer_id:
            return

        result = await self.db.execute(
            select(PayoutRequest).where(
                PayoutRequest.stripe_transfer_id == transfer_id
            )
        )
        payout = result.scalar_one_or_none()
        if not payout:
            logger.debug("No payout found for transfer %s", transfer_id)
            return

        if event_type == "transfer.paid":
            payout.status = PayoutStatus.COMPLETED
            payout.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            logger.info("Payout %s completed (transfer %s)", payout.id, transfer_id)

        elif event_type == "transfer.failed":
            failure_reason = transfer.get("failure_message") or "Transfer failed"
            payout.status = PayoutStatus.FAILED
            payout.failure_reason = failure_reason[:500]

            # Refund credits back to user
            stmt = (
                select(Account)
                .where(Account.owner_id == payout.user_id)
                .with_for_update()
            )
            result = await self.db.execute(stmt)
            account = result.scalars().first()
            if account:
                account.balance += Decimal(str(payout.amount_credits))
                # Record refund transaction
                refund_txn = Transaction(
                    from_account_id=None,
                    to_account_id=account.id,
                    amount=Decimal(str(payout.amount_credits)),
                    type=TransactionType.REFUND,
                    description=f"Payout refund — transfer {transfer_id} failed",
                )
                self.db.add(refund_txn)

            await self.db.commit()
            logger.warning(
                "Payout %s failed (transfer %s): %s — credits refunded",
                payout.id, transfer_id, failure_reason,
            )
