"""Revision cf008 — core_assets, core_inventory (Sprint 10)."""
from alembic import op
import sqlalchemy as sa

revision = "cf008_assets_inventory"
down_revision = "cf007_orders_invoices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Cria inventory_items legado, core_assets e core_inventory."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "inventory_items" not in tables:
        op.create_table(
            "inventory_items",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("sku", sa.String(), nullable=True),
            sa.Column("asset_type", sa.String(), nullable=False),
            sa.Column("unit", sa.String(), nullable=False),
            sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
            sa.Column("reorder_level", sa.Numeric(10, 2), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_inventory_items_company_id"), "inventory_items", ["company_id"], unique=False)
        op.create_index(op.f("ix_inventory_items_id"), "inventory_items", ["id"], unique=False)
        op.create_index(op.f("ix_inventory_items_name"), "inventory_items", ["name"], unique=False)
        op.create_index(op.f("ix_inventory_items_sku"), "inventory_items", ["sku"], unique=False)

    if "core_assets" not in tables:
        op.create_table(
            "core_assets",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("sku", sa.String(), nullable=True),
            sa.Column("asset_type", sa.String(), nullable=False),
            sa.Column("unit", sa.String(), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False),
            sa.Column("plugin_metadata", sa.JSON(), nullable=True),
            sa.Column("legacy_inventory_item_id", sa.Integer(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("legacy_inventory_item_id", name="uq_core_asset_legacy_inventory"),
        )
        op.create_index(op.f("ix_core_assets_asset_type"), "core_assets", ["asset_type"], unique=False)
        op.create_index(op.f("ix_core_assets_company_id"), "core_assets", ["company_id"], unique=False)
        op.create_index(op.f("ix_core_assets_id"), "core_assets", ["id"], unique=False)
        op.create_index(op.f("ix_core_assets_legacy_inventory_item_id"), "core_assets", ["legacy_inventory_item_id"], unique=False)
        op.create_index(op.f("ix_core_assets_name"), "core_assets", ["name"], unique=False)
        op.create_index(op.f("ix_core_assets_sku"), "core_assets", ["sku"], unique=False)

    if "core_inventory" not in tables:
        op.create_table(
            "core_inventory",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("asset_id", sa.Integer(), nullable=False),
            sa.Column("quantity_on_hand", sa.Numeric(10, 2), nullable=False),
            sa.Column("reorder_level", sa.Numeric(10, 2), nullable=False),
            sa.Column("legacy_inventory_item_id", sa.Integer(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["asset_id"], ["core_assets.id"]),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("legacy_inventory_item_id", name="uq_core_inventory_legacy"),
        )
        op.create_index(op.f("ix_core_inventory_asset_id"), "core_inventory", ["asset_id"], unique=False)
        op.create_index(op.f("ix_core_inventory_company_id"), "core_inventory", ["company_id"], unique=False)
        op.create_index(op.f("ix_core_inventory_id"), "core_inventory", ["id"], unique=False)
        op.create_index(op.f("ix_core_inventory_legacy_inventory_item_id"), "core_inventory", ["legacy_inventory_item_id"], unique=False)


def downgrade() -> None:
    """Remove tabelas CF-10."""
    op.drop_index(op.f("ix_core_inventory_legacy_inventory_item_id"), table_name="core_inventory")
    op.drop_index(op.f("ix_core_inventory_id"), table_name="core_inventory")
    op.drop_index(op.f("ix_core_inventory_company_id"), table_name="core_inventory")
    op.drop_index(op.f("ix_core_inventory_asset_id"), table_name="core_inventory")
    op.drop_table("core_inventory")

    op.drop_index(op.f("ix_core_assets_sku"), table_name="core_assets")
    op.drop_index(op.f("ix_core_assets_name"), table_name="core_assets")
    op.drop_index(op.f("ix_core_assets_legacy_inventory_item_id"), table_name="core_assets")
    op.drop_index(op.f("ix_core_assets_id"), table_name="core_assets")
    op.drop_index(op.f("ix_core_assets_company_id"), table_name="core_assets")
    op.drop_index(op.f("ix_core_assets_asset_type"), table_name="core_assets")
    op.drop_table("core_assets")

    op.drop_index(op.f("ix_inventory_items_sku"), table_name="inventory_items")
    op.drop_index(op.f("ix_inventory_items_name"), table_name="inventory_items")
    op.drop_index(op.f("ix_inventory_items_id"), table_name="inventory_items")
    op.drop_index(op.f("ix_inventory_items_company_id"), table_name="inventory_items")
    op.drop_table("inventory_items")
