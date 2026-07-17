"""CoreFlow metamodelo — Catalog, Offering, Booking (Sprint 1).

Revision ID: cf001_metamodel
Revises:
Create Date: 2026-07-09

"""
from alembic import op
import sqlalchemy as sa


revision = "cf001_metamodel"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Cria tabelas core_catalogs, core_offerings e core_bookings.

    Idempotente em bancos novos; em SQLite existentes, ``create_all`` pode
    já ter criado — Alembic registra baseline para MySQL/produção.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "core_catalogs" not in existing:
        op.create_table(
            "core_catalogs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("slug", sa.String(255), nullable=False),
            sa.Column("description", sa.String(255), nullable=True),
            sa.Column("images", sa.JSON(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False),
            sa.Column("plugin_metadata", sa.JSON(), nullable=True),
            sa.Column("legacy_tranca_id", sa.Integer(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "slug", name="uq_core_catalog_company_slug"),
            sa.UniqueConstraint("legacy_tranca_id", name="uq_core_catalog_legacy_tranca"),
        )
        op.create_index(op.f("ix_core_catalogs_company_id"), "core_catalogs", ["company_id"], unique=False)
        op.create_index(op.f("ix_core_catalogs_id"), "core_catalogs", ["id"], unique=False)
        op.create_index(op.f("ix_core_catalogs_legacy_tranca_id"), "core_catalogs", ["legacy_tranca_id"], unique=False)
        op.create_index(op.f("ix_core_catalogs_name"), "core_catalogs", ["name"], unique=False)
        op.create_index(op.f("ix_core_catalogs_slug"), "core_catalogs", ["slug"], unique=False)

    if "core_offerings" not in existing:
        op.create_table(
            "core_offerings",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("catalog_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(255), nullable=True),
            sa.Column("description", sa.String(255), nullable=True),
            sa.Column("price_total", sa.Numeric(10, 2), nullable=True),
            sa.Column("deposit_pct", sa.Numeric(5, 4), nullable=True),
            sa.Column("deposit_amount", sa.Numeric(10, 2), nullable=True),
            sa.Column("duration_minutes", sa.Integer(), nullable=True),
            sa.Column("image_url", sa.String(255), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False),
            sa.Column("plugin_metadata", sa.JSON(), nullable=True),
            sa.Column("legacy_service_image_id", sa.Integer(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["catalog_id"], ["core_catalogs.id"]),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("legacy_service_image_id", name="uq_core_offering_legacy_image"),
        )
        op.create_index(op.f("ix_core_offerings_catalog_id"), "core_offerings", ["catalog_id"], unique=False)
        op.create_index(op.f("ix_core_offerings_company_id"), "core_offerings", ["company_id"], unique=False)
        op.create_index(op.f("ix_core_offerings_id"), "core_offerings", ["id"], unique=False)
        op.create_index(op.f("ix_core_offerings_legacy_service_image_id"), "core_offerings", ["legacy_service_image_id"], unique=False)

    if "core_bookings" not in existing:
        op.create_table(
            "core_bookings",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("customer_id", sa.Integer(), nullable=False),
            sa.Column("catalog_id", sa.Integer(), nullable=False),
            sa.Column("offering_id", sa.Integer(), nullable=False),
            sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(255), nullable=False),
            sa.Column("payment_status", sa.String(255), nullable=False),
            sa.Column("price_total", sa.Numeric(10, 2), nullable=False),
            sa.Column("deposit_pct", sa.Numeric(5, 4), nullable=False),
            sa.Column("deposit_amount", sa.Numeric(10, 2), nullable=False),
            sa.Column("remaining_amount", sa.Numeric(10, 2), nullable=False),
            sa.Column("deposit_paid", sa.Boolean(), nullable=False),
            sa.Column("notes", sa.String(255), nullable=True),
            sa.Column("legacy_agendamento_id", sa.Integer(), nullable=True),
            sa.Column("sync_status", sa.String(255), nullable=False, server_default="synced"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["catalog_id"], ["core_catalogs.id"]),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["customer_id"], ["clientes.id"]),
            sa.ForeignKeyConstraint(["offering_id"], ["core_offerings.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("legacy_agendamento_id", name="uq_core_booking_legacy_agendamento"),
        )
        op.create_index(op.f("ix_core_bookings_catalog_id"), "core_bookings", ["catalog_id"], unique=False)
        op.create_index(op.f("ix_core_bookings_company_id"), "core_bookings", ["company_id"], unique=False)
        op.create_index(op.f("ix_core_bookings_customer_id"), "core_bookings", ["customer_id"], unique=False)
        op.create_index(op.f("ix_core_bookings_id"), "core_bookings", ["id"], unique=False)
        op.create_index(op.f("ix_core_bookings_legacy_agendamento_id"), "core_bookings", ["legacy_agendamento_id"], unique=False)
        op.create_index(op.f("ix_core_bookings_offering_id"), "core_bookings", ["offering_id"], unique=False)
        op.create_index(op.f("ix_core_bookings_scheduled_at"), "core_bookings", ["scheduled_at"], unique=False)
        op.create_index(op.f("ix_core_bookings_status"), "core_bookings", ["status"], unique=False)


def downgrade() -> None:
    """Remove tabelas do metamodelo Sprint 1."""
    op.drop_index(op.f("ix_core_bookings_status"), table_name="core_bookings")
    op.drop_index(op.f("ix_core_bookings_scheduled_at"), table_name="core_bookings")
    op.drop_index(op.f("ix_core_bookings_offering_id"), table_name="core_bookings")
    op.drop_index(op.f("ix_core_bookings_legacy_agendamento_id"), table_name="core_bookings")
    op.drop_index(op.f("ix_core_bookings_id"), table_name="core_bookings")
    op.drop_index(op.f("ix_core_bookings_customer_id"), table_name="core_bookings")
    op.drop_index(op.f("ix_core_bookings_company_id"), table_name="core_bookings")
    op.drop_index(op.f("ix_core_bookings_catalog_id"), table_name="core_bookings")
    op.drop_table("core_bookings")
    op.drop_index(op.f("ix_core_offerings_legacy_service_image_id"), table_name="core_offerings")
    op.drop_index(op.f("ix_core_offerings_id"), table_name="core_offerings")
    op.drop_index(op.f("ix_core_offerings_company_id"), table_name="core_offerings")
    op.drop_index(op.f("ix_core_offerings_catalog_id"), table_name="core_offerings")
    op.drop_table("core_offerings")
    op.drop_index(op.f("ix_core_catalogs_slug"), table_name="core_catalogs")
    op.drop_index(op.f("ix_core_catalogs_name"), table_name="core_catalogs")
    op.drop_index(op.f("ix_core_catalogs_legacy_tranca_id"), table_name="core_catalogs")
    op.drop_index(op.f("ix_core_catalogs_id"), table_name="core_catalogs")
    op.drop_index(op.f("ix_core_catalogs_company_id"), table_name="core_catalogs")
    op.drop_table("core_catalogs")
