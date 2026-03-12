"""Add Stripe Connect columns to users and create payout_requests table.

Revision ID: 022
Revises: 021
"""

import sqlalchemy as sa
from alembic import op

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    is_pg = conn.dialect.name == "postgresql"

    # --- Users: Stripe Connect columns ---
    op.add_column("users", sa.Column(
        "stripe_connect_account_id", sa.String(255), nullable=True, unique=True,
    ))
    op.add_column("users", sa.Column(
        "stripe_connect_onboarded", sa.Boolean(), nullable=False, server_default=sa.text("false"),
    ))
    op.add_column("users", sa.Column(
        "stripe_connect_payouts_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false"),
    ))
    op.create_index("ix_users_stripe_connect_account_id", "users", ["stripe_connect_account_id"], unique=True)

    # --- Payout requests table ---
    op.create_table(
        "payout_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("amount_credits", sa.Numeric(16, 4), nullable=False),
        sa.Column("amount_usd_cents", sa.Integer(), nullable=False),
        sa.Column("stripe_fee_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending", index=True),
        sa.Column("stripe_transfer_id", sa.String(255), nullable=True, unique=True),
        sa.Column("failure_reason", sa.String(500), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- Extend TransactionType enum (PostgreSQL only) ---
    if is_pg:
        op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'payout'")


def downgrade() -> None:
    op.drop_table("payout_requests")
    op.drop_index("ix_users_stripe_connect_account_id", table_name="users")
    op.drop_column("users", "stripe_connect_payouts_enabled")
    op.drop_column("users", "stripe_connect_onboarded")
    op.drop_column("users", "stripe_connect_account_id")
    # Note: PostgreSQL enum values cannot be removed without recreating the type
