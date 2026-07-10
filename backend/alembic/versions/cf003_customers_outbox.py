"""Revision cf003 — core_customers + core_event_outbox (Sprint 5)."""
from alembic import op
import sqlalchemy as sa

revision = "cf003_customers_outbox"
down_revision = "cf002_scheduling"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Cria core_customers e core_event_outbox."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "core_customers" not in existing:
        op.create_table(
            "core_customers",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("phone", sa.String(), nullable=False),
            sa.Column("email", sa.String(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False),
            sa.Column("plugin_metadata", sa.JSON(), nullable=True),
            sa.Column("legacy_cliente_id", sa.Integer(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("legacy_cliente_id", name="uq_core_customer_legacy"),
            sa.UniqueConstraint("company_id", "phone", name="uq_core_customer_company_phone"),
        )
        op.create_index(op.f("ix_core_customers_company_id"), "core_customers", ["company_id"], unique=False)
        op.create_index(op.f("ix_core_customers_id"), "core_customers", ["id"], unique=False)
        op.create_index(op.f("ix_core_customers_legacy_cliente_id"), "core_customers", ["legacy_cliente_id"], unique=False)
        op.create_index(op.f("ix_core_customers_name"), "core_customers", ["name"], unique=False)
        op.create_index(op.f("ix_core_customers_phone"), "core_customers", ["phone"], unique=False)

    if "core_event_outbox" not in existing:
        op.create_table(
            "core_event_outbox",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("event_id", sa.String(), nullable=False),
            sa.Column("event_type", sa.String(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("aggregate_id", sa.String(), nullable=True),
            sa.Column("aggregate_type", sa.String(), nullable=True),
            sa.Column("payload", sa.Text(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("event_id", name="uq_core_event_outbox_event_id"),
        )
        op.create_index(op.f("ix_core_event_outbox_company_id"), "core_event_outbox", ["company_id"], unique=False)
        op.create_index(op.f("ix_core_event_outbox_event_id"), "core_event_outbox", ["event_id"], unique=False)
        op.create_index(op.f("ix_core_event_outbox_event_type"), "core_event_outbox", ["event_type"], unique=False)
        op.create_index(op.f("ix_core_event_outbox_id"), "core_event_outbox", ["id"], unique=False)
        op.create_index(op.f("ix_core_event_outbox_status"), "core_event_outbox", ["status"], unique=False)


def downgrade() -> None:
    """Remove tabelas Sprint 5."""
    op.drop_index(op.f("ix_core_event_outbox_status"), table_name="core_event_outbox")
    op.drop_index(op.f("ix_core_event_outbox_id"), table_name="core_event_outbox")
    op.drop_index(op.f("ix_core_event_outbox_event_type"), table_name="core_event_outbox")
    op.drop_index(op.f("ix_core_event_outbox_event_id"), table_name="core_event_outbox")
    op.drop_index(op.f("ix_core_event_outbox_company_id"), table_name="core_event_outbox")
    op.drop_table("core_event_outbox")
    op.drop_index(op.f("ix_core_customers_phone"), table_name="core_customers")
    op.drop_index(op.f("ix_core_customers_name"), table_name="core_customers")
    op.drop_index(op.f("ix_core_customers_legacy_cliente_id"), table_name="core_customers")
    op.drop_index(op.f("ix_core_customers_id"), table_name="core_customers")
    op.drop_index(op.f("ix_core_customers_company_id"), table_name="core_customers")
    op.drop_table("core_customers")
