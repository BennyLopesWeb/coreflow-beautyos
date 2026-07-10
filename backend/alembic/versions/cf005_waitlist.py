"""Revision cf005 — core_waitlist (Sprint 7)."""
from alembic import op
import sqlalchemy as sa

revision = "cf005_waitlist"
down_revision = "cf004_payments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Cria core_waitlist."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "core_waitlist" in inspector.get_table_names():
        return

    op.create_table(
        "core_waitlist",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("catalog_id", sa.Integer(), nullable=True),
        sa.Column("offering_id", sa.Integer(), nullable=True),
        sa.Column("preferred_date", sa.Date(), nullable=False),
        sa.Column("preferred_time", sa.Time(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("same_day", sa.Boolean(), nullable=False),
        sa.Column("legacy_fila_id", sa.Integer(), nullable=True),
        sa.Column("legacy_cliente_id", sa.Integer(), nullable=True),
        sa.Column("legacy_tranca_id", sa.Integer(), nullable=True),
        sa.Column("legacy_service_image_id", sa.Integer(), nullable=True),
        sa.Column("plugin_metadata", sa.JSON(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["booking_id"], ["core_bookings.id"]),
        sa.ForeignKeyConstraint(["catalog_id"], ["core_catalogs.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["core_customers.id"]),
        sa.ForeignKeyConstraint(["offering_id"], ["core_offerings.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("legacy_fila_id", name="uq_core_waitlist_legacy"),
    )
    op.create_index(op.f("ix_core_waitlist_booking_id"), "core_waitlist", ["booking_id"], unique=False)
    op.create_index(op.f("ix_core_waitlist_catalog_id"), "core_waitlist", ["catalog_id"], unique=False)
    op.create_index(op.f("ix_core_waitlist_company_id"), "core_waitlist", ["company_id"], unique=False)
    op.create_index(op.f("ix_core_waitlist_customer_id"), "core_waitlist", ["customer_id"], unique=False)
    op.create_index(op.f("ix_core_waitlist_id"), "core_waitlist", ["id"], unique=False)
    op.create_index(op.f("ix_core_waitlist_legacy_cliente_id"), "core_waitlist", ["legacy_cliente_id"], unique=False)
    op.create_index(op.f("ix_core_waitlist_legacy_fila_id"), "core_waitlist", ["legacy_fila_id"], unique=False)
    op.create_index(op.f("ix_core_waitlist_legacy_service_image_id"), "core_waitlist", ["legacy_service_image_id"], unique=False)
    op.create_index(op.f("ix_core_waitlist_legacy_tranca_id"), "core_waitlist", ["legacy_tranca_id"], unique=False)
    op.create_index(op.f("ix_core_waitlist_offering_id"), "core_waitlist", ["offering_id"], unique=False)
    op.create_index(op.f("ix_core_waitlist_preferred_date"), "core_waitlist", ["preferred_date"], unique=False)
    op.create_index(op.f("ix_core_waitlist_status"), "core_waitlist", ["status"], unique=False)


def downgrade() -> None:
    """Remove core_waitlist."""
    op.drop_index(op.f("ix_core_waitlist_status"), table_name="core_waitlist")
    op.drop_index(op.f("ix_core_waitlist_preferred_date"), table_name="core_waitlist")
    op.drop_index(op.f("ix_core_waitlist_offering_id"), table_name="core_waitlist")
    op.drop_index(op.f("ix_core_waitlist_legacy_tranca_id"), table_name="core_waitlist")
    op.drop_index(op.f("ix_core_waitlist_legacy_service_image_id"), table_name="core_waitlist")
    op.drop_index(op.f("ix_core_waitlist_legacy_fila_id"), table_name="core_waitlist")
    op.drop_index(op.f("ix_core_waitlist_legacy_cliente_id"), table_name="core_waitlist")
    op.drop_index(op.f("ix_core_waitlist_id"), table_name="core_waitlist")
    op.drop_index(op.f("ix_core_waitlist_customer_id"), table_name="core_waitlist")
    op.drop_index(op.f("ix_core_waitlist_company_id"), table_name="core_waitlist")
    op.drop_index(op.f("ix_core_waitlist_catalog_id"), table_name="core_waitlist")
    op.drop_index(op.f("ix_core_waitlist_booking_id"), table_name="core_waitlist")
    op.drop_table("core_waitlist")
