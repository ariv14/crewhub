# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Add orchestration pattern columns, supervisor_plans table, and sub-workflow support.

Revision ID: 028
Revises: 027
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- New columns on workflows --
    op.add_column("workflows", sa.Column("pattern_type", sa.String(50), nullable=False, server_default="manual"))
    op.add_column("workflows", sa.Column("supervisor_config", postgresql.JSON(), nullable=True))

    # -- Alter workflow_steps: make agent_id and skill_id nullable --
    op.alter_column("workflow_steps", "agent_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.alter_column("workflow_steps", "skill_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)

    # -- New column on workflow_steps --
    op.add_column("workflow_steps", sa.Column("sub_workflow_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_workflow_steps_sub_workflow",
        "workflow_steps", "workflows",
        ["sub_workflow_id"], ["id"],
        ondelete="SET NULL",
    )

    # -- New columns on workflow_runs --
    op.add_column("workflow_runs", sa.Column("parent_run_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_workflow_runs_parent_run",
        "workflow_runs", "workflow_runs",
        ["parent_run_id"], ["id"],
        ondelete="SET NULL",
    )
    op.add_column("workflow_runs", sa.Column("depth", sa.Integer(), nullable=False, server_default="0"))

    # -- New column on workflow_step_runs --
    op.add_column("workflow_step_runs", sa.Column("child_run_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_workflow_step_runs_child_run",
        "workflow_step_runs", "workflow_runs",
        ["child_run_id"], ["id"],
        ondelete="SET NULL",
    )

    # -- New table: supervisor_plans --
    op.create_table(
        "supervisor_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("goal", sa.String(2000), nullable=False),
        sa.Column("plan_data", postgresql.JSON(), nullable=False),
        sa.Column("llm_provider", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    # 1. Drop supervisor_plans table
    op.drop_table("supervisor_plans")

    # 2. Drop FK on workflow_step_runs, then column
    op.drop_constraint("fk_workflow_step_runs_child_run", "workflow_step_runs", type_="foreignkey")
    op.drop_column("workflow_step_runs", "child_run_id")

    # 3. Drop FK + columns on workflow_runs
    op.drop_constraint("fk_workflow_runs_parent_run", "workflow_runs", type_="foreignkey")
    op.drop_column("workflow_runs", "depth")
    op.drop_column("workflow_runs", "parent_run_id")

    # 4. Drop FK + column on workflow_steps
    op.drop_constraint("fk_workflow_steps_sub_workflow", "workflow_steps", type_="foreignkey")
    op.drop_column("workflow_steps", "sub_workflow_id")

    # 5. Alter agent_id/skill_id back to NOT NULL
    op.alter_column("workflow_steps", "skill_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.alter_column("workflow_steps", "agent_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)

    # 6. Drop columns on workflows
    op.drop_column("workflows", "supervisor_config")
    op.drop_column("workflows", "pattern_type")
