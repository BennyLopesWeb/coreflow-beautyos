"""Revision cf007 — core_orders, core_invoices, core_workflow_config (Sprint 9)."""
from alembic import op
import sqlalchemy as sa

revision = "cf007_orders_invoices"
down_revision = "cf006_workflow_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Cria core_orders, core_invoices e core_workflow_config."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "core_orders" not in tables:
        op.create_table(
            "core_orders",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("booking_id", sa.Integer(), nullable=True),
            sa.Column("customer_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
            sa.Column("paid_amount", sa.Numeric(10, 2), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False),
            sa.Column("legacy_agendamento_id", sa.Integer(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["booking_id"], ["core_bookings.id"]),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["customer_id"], ["clientes.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("legacy_agendamento_id", name="uq_core_order_legacy_agendamento"),
        )
        op.create_index(op.f("ix_core_orders_booking_id"), "core_orders", ["booking_id"], unique=False)
        op.create_index(op.f("ix_core_orders_company_id"), "core_orders", ["company_id"], unique=False)
        op.create_index(op.f("ix_core_orders_customer_id"), "core_orders", ["customer_id"], unique=False)
        op.create_index(op.f("ix_core_orders_id"), "core_orders", ["id"], unique=False)
        op.create_index(op.f("ix_core_orders_legacy_agendamento_id"), "core_orders", ["legacy_agendamento_id"], unique=False)
        op.create_index(op.f("ix_core_orders_status"), "core_orders", ["status"], unique=False)

    if "core_invoices" not in tables:
        op.create_table(
            "core_invoices",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("order_id", sa.Integer(), nullable=True),
            sa.Column("booking_id", sa.Integer(), nullable=True),
            sa.Column("invoice_number", sa.String(), nullable=False),
            sa.Column("description", sa.String(), nullable=False),
            sa.Column("amount", sa.Numeric(10, 2), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("legacy_financeiro_id", sa.Integer(), nullable=True),
            sa.Column("legacy_agendamento_id", sa.Integer(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["booking_id"], ["core_bookings.id"]),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["order_id"], ["core_orders.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("legacy_financeiro_id", name="uq_core_invoice_legacy_financeiro"),
        )
        op.create_index(op.f("ix_core_invoices_booking_id"), "core_invoices", ["booking_id"], unique=False)
        op.create_index(op.f("ix_core_invoices_company_id"), "core_invoices", ["company_id"], unique=False)
        op.create_index(op.f("ix_core_invoices_id"), "core_invoices", ["id"], unique=False)
        op.create_index(op.f("ix_core_invoices_invoice_number"), "core_invoices", ["invoice_number"], unique=False)
        op.create_index(op.f("ix_core_invoices_legacy_agendamento_id"), "core_invoices", ["legacy_agendamento_id"], unique=False)
        op.create_index(op.f("ix_core_invoices_legacy_financeiro_id"), "core_invoices", ["legacy_financeiro_id"], unique=False)
        op.create_index(op.f("ix_core_invoices_order_id"), "core_invoices", ["order_id"], unique=False)
        op.create_index(op.f("ix_core_invoices_status"), "core_invoices", ["status"], unique=False)

    if "core_workflow_config" not in tables:
        op.create_table(
            "core_workflow_config",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=True),
            sa.Column("workflow_id", sa.String(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "workflow_id", name="uq_workflow_config_company"),
        )
        op.create_index(op.f("ix_core_workflow_config_company_id"), "core_workflow_config", ["company_id"], unique=False)
        op.create_index(op.f("ix_core_workflow_config_id"), "core_workflow_config", ["id"], unique=False)
        op.create_index(op.f("ix_core_workflow_config_workflow_id"), "core_workflow_config", ["workflow_id"], unique=False)


def downgrade() -> None:
    """Remove tabelas CF-9."""
    op.drop_index(op.f("ix_core_workflow_config_workflow_id"), table_name="core_workflow_config")
    op.drop_index(op.f("ix_core_workflow_config_id"), table_name="core_workflow_config")
    op.drop_index(op.f("ix_core_workflow_config_company_id"), table_name="core_workflow_config")
    op.drop_table("core_workflow_config")

    op.drop_index(op.f("ix_core_invoices_status"), table_name="core_invoices")
    op.drop_index(op.f("ix_core_invoices_order_id"), table_name="core_invoices")
    op.drop_index(op.f("ix_core_invoices_legacy_financeiro_id"), table_name="core_invoices")
    op.drop_index(op.f("ix_core_invoices_legacy_agendamento_id"), table_name="core_invoices")
    op.drop_index(op.f("ix_core_invoices_invoice_number"), table_name="core_invoices")
    op.drop_index(op.f("ix_core_invoices_id"), table_name="core_invoices")
    op.drop_index(op.f("ix_core_invoices_company_id"), table_name="core_invoices")
    op.drop_index(op.f("ix_core_invoices_booking_id"), table_name="core_invoices")
    op.drop_table("core_invoices")

    op.drop_index(op.f("ix_core_orders_status"), table_name="core_orders")
    op.drop_index(op.f("ix_core_orders_legacy_agendamento_id"), table_name="core_orders")
    op.drop_index(op.f("ix_core_orders_id"), table_name="core_orders")
    op.drop_index(op.f("ix_core_orders_customer_id"), table_name="core_orders")
    op.drop_index(op.f("ix_core_orders_company_id"), table_name="core_orders")
    op.drop_index(op.f("ix_core_orders_booking_id"), table_name="core_orders")
    op.drop_table("core_orders")
