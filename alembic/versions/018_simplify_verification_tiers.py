"""Simplify verification_level from 5 tiers to 3.

Revision ID: 018
Revises: 017
"""

from alembic import op

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Map old 5-tier values to new 3-tier system
    op.execute("UPDATE agents SET verification_level = 'new' WHERE verification_level = 'unverified'")
    op.execute("UPDATE agents SET verification_level = 'verified' WHERE verification_level IN ('self_tested', 'namespace_verified')")
    op.execute("UPDATE agents SET verification_level = 'certified' WHERE verification_level IN ('quality_assured', 'audit_passed')")


def downgrade() -> None:
    # Reverse: map back to original values (lossy — self_tested vs namespace_verified indistinguishable)
    op.execute("UPDATE agents SET verification_level = 'unverified' WHERE verification_level = 'new'")
    op.execute("UPDATE agents SET verification_level = 'self_tested' WHERE verification_level = 'verified'")
    op.execute("UPDATE agents SET verification_level = 'quality_assured' WHERE verification_level = 'certified'")
