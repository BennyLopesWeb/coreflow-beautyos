"""Revision cf004 — core_payments (Sprint 6)."""
from alembic import op
import sqlalchemy as sa

revision = "cf004_payments"
down_revision = "cf003_customers_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Cria core_payments."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "core_payments" in inspector.get_table_names():
        return

    op.create_table(
        "core_payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=True),
        sa.Column("payment_type", sa.String(255), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(255), nullable=False),
        sa.Column("transaction_id", sa.String(255), nullable=True),
        sa.Column("receipt_url", sa.String(255), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("legacy_payment_id", sa.Integer(), nullable=True),
        sa.Column("legacy_agendamento_id", sa.Integer(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["booking_id"], ["core_bookings.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("legacy_payment_id", name="uq_core_payment_legacy"),
    )
    op.create_index(op.f("ix_core_payments_booking_id"), "core_payments", ["booking_id"], unique=False)
    op.create_index(op.f("ix_core_payments_company_id"), "core_payments", ["company_id"], unique=False)
    op.create_index(op.f("ix_core_payments_id"), "core_payments", ["id"], unique=False)
    op.create_index(op.f("ix_core_payments_legacy_agendamento_id"), "core_payments", ["legacy_agendamento_id"], unique=False)
    op.create_index(op.f("ix_core_payments_legacy_payment_id"), "core_payments", ["legacy_payment_id"], unique=False)
    op.create_index(op.f("ix_core_payments_payment_type"), "core_payments", ["payment_type"], unique=False)
    op.create_index(op.f("ix_core_payments_status"), "core_payments", ["status"], unique=False)
    op.create_index(op.f("ix_core_payments_transaction_id"), "core_payments", ["transaction_id"], unique=False)


def downgrade() -> None:
    """Remove core_payments."""
    op.drop_index(op.f("ix_core_payments_transaction_id"), table_name="core_payments")
    op.drop_index(op.f("ix_core_payments_status"), table_name="core_payments")
    op.drop_index(op.f("ix_core_payments_payment_type"), table_name="core_payments")
    op.drop_index(op.f("ix_core_payments_legacy_payment_id"), table_name="core_payments")
    op.drop_index(op.f("ix_core_payments_legacy_agendamento_id"), table_name="core_payments")
    op.drop_index(op.f("ix_core_payments_id"), table_name="core_payments")
    op.drop_index(op.f("ix_core_payments_company_id"), table_name="core_payments")
    op.drop_index(op.f("ix_core_payments_booking_id"), table_name="core_payments")
    op.drop_table("core_payments")
