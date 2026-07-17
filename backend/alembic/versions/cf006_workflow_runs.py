"""Revision cf006 — core_workflow_runs (Sprint 8)."""
from alembic import op
import sqlalchemy as sa

revision = "cf006_workflow_runs"
down_revision = "cf005_waitlist"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Cria core_workflow_runs."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "core_workflow_runs" in inspector.get_table_names():
        return

    op.create_table(
        "core_workflow_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("workflow_id", sa.String(255), nullable=False),
        sa.Column("trigger_event_type", sa.String(255), nullable=False),
        sa.Column("trigger_event_id", sa.String(255), nullable=True),
        sa.Column("aggregate_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("steps_executed", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_core_workflow_runs_aggregate_id"), "core_workflow_runs", ["aggregate_id"], unique=False)
    op.create_index(op.f("ix_core_workflow_runs_company_id"), "core_workflow_runs", ["company_id"], unique=False)
    op.create_index(op.f("ix_core_workflow_runs_id"), "core_workflow_runs", ["id"], unique=False)
    op.create_index(op.f("ix_core_workflow_runs_status"), "core_workflow_runs", ["status"], unique=False)
    op.create_index(op.f("ix_core_workflow_runs_trigger_event_id"), "core_workflow_runs", ["trigger_event_id"], unique=False)
    op.create_index(op.f("ix_core_workflow_runs_trigger_event_type"), "core_workflow_runs", ["trigger_event_type"], unique=False)
    op.create_index(op.f("ix_core_workflow_runs_workflow_id"), "core_workflow_runs", ["workflow_id"], unique=False)


def downgrade() -> None:
    """Remove core_workflow_runs."""
    op.drop_index(op.f("ix_core_workflow_runs_workflow_id"), table_name="core_workflow_runs")
    op.drop_index(op.f("ix_core_workflow_runs_trigger_event_type"), table_name="core_workflow_runs")
    op.drop_index(op.f("ix_core_workflow_runs_trigger_event_id"), table_name="core_workflow_runs")
    op.drop_index(op.f("ix_core_workflow_runs_status"), table_name="core_workflow_runs")
    op.drop_index(op.f("ix_core_workflow_runs_id"), table_name="core_workflow_runs")
    op.drop_index(op.f("ix_core_workflow_runs_company_id"), table_name="core_workflow_runs")
    op.drop_index(op.f("ix_core_workflow_runs_aggregate_id"), table_name="core_workflow_runs")
    op.drop_table("core_workflow_runs")
