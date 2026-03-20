"""Recover agents mass-deactivated by health monitor.

One-time data fix: agents with status='inactive' AND
capabilities->>'_health_failures' >= '3' were deactivated by the
health monitor (not by owners). Set them back to 'active' and
reset the failure counter.

Revision ID: 033
Revises: 032
"""
from alembic import op

revision = "033"
down_revision = "032"


def upgrade() -> None:
    # Reactivate agents that were deactivated by the health monitor
    # (owner-deactivated agents have _health_failures = 0 or no key)
    op.execute("""
        UPDATE agents
        SET status = 'active',
            capabilities = jsonb_set(
                COALESCE(capabilities, '{}')::jsonb,
                '{_health_failures}',
                '0'
            )
        WHERE status = 'inactive'
          AND COALESCE(capabilities, '{}')::jsonb->>'_health_failures' IS NOT NULL
          AND (COALESCE(capabilities, '{}')::jsonb->>'_health_failures')::int >= 3
    """)


def downgrade() -> None:
    # Cannot reliably undo — agents may have been re-deactivated since
    pass
