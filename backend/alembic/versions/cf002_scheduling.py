"""CoreFlow scheduling — Location, Worker, Resource, ScheduleBlock (Sprint 2).

Revision ID: cf002_scheduling
Revises: cf001_metamodel
Create Date: 2026-07-09

"""
from alembic import op
import sqlalchemy as sa


revision = "cf002_scheduling"
down_revision = "cf001_metamodel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Cria tabelas de scheduling genérico CoreFlow.

    Returns:
        None
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "core_locations" not in existing:
        op.create_table(
            "core_locations",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("slug", sa.String(), nullable=False),
            sa.Column("address", sa.JSON(), nullable=True),
            sa.Column("timezone", sa.String(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False),
            sa.Column("is_default", sa.Boolean(), nullable=False),
            sa.Column("plugin_metadata", sa.JSON(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "slug", name="uq_core_location_company_slug"),
        )
        op.create_index(op.f("ix_core_locations_company_id"), "core_locations", ["company_id"], unique=False)
        op.create_index(op.f("ix_core_locations_id"), "core_locations", ["id"], unique=False)
        op.create_index(op.f("ix_core_locations_name"), "core_locations", ["name"], unique=False)
        op.create_index(op.f("ix_core_locations_slug"), "core_locations", ["slug"], unique=False)

    if "core_workers" not in existing:
        op.create_table(
            "core_workers",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("display_name", sa.String(), nullable=False),
            sa.Column("email", sa.String(), nullable=True),
            sa.Column("role", sa.String(), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False),
            sa.Column("plugin_metadata", sa.JSON(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "user_id", name="uq_core_worker_company_user"),
        )
        op.create_index(op.f("ix_core_workers_company_id"), "core_workers", ["company_id"], unique=False)
        op.create_index(op.f("ix_core_workers_id"), "core_workers", ["id"], unique=False)
        op.create_index(op.f("ix_core_workers_user_id"), "core_workers", ["user_id"], unique=False)

    if "core_resources" not in existing:
        op.create_table(
            "core_resources",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("location_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("slug", sa.String(), nullable=False),
            sa.Column("resource_type", sa.String(), nullable=False),
            sa.Column("capacity", sa.Integer(), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False),
            sa.Column("is_default", sa.Boolean(), nullable=False),
            sa.Column("plugin_metadata", sa.JSON(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["location_id"], ["core_locations.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "slug", name="uq_core_resource_company_slug"),
        )
        op.create_index(op.f("ix_core_resources_company_id"), "core_resources", ["company_id"], unique=False)
        op.create_index(op.f("ix_core_resources_id"), "core_resources", ["id"], unique=False)
        op.create_index(op.f("ix_core_resources_location_id"), "core_resources", ["location_id"], unique=False)
        op.create_index(op.f("ix_core_resources_slug"), "core_resources", ["slug"], unique=False)

    if "core_schedule_blocks" not in existing:
        op.create_table(
            "core_schedule_blocks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("booking_id", sa.Integer(), nullable=True),
            sa.Column("resource_id", sa.Integer(), nullable=False),
            sa.Column("worker_id", sa.Integer(), nullable=True),
            sa.Column("location_id", sa.Integer(), nullable=False),
            sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("legacy_schedule_id", sa.Integer(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["booking_id"], ["core_bookings.id"]),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["location_id"], ["core_locations.id"]),
            sa.ForeignKeyConstraint(["resource_id"], ["core_resources.id"]),
            sa.ForeignKeyConstraint(["worker_id"], ["core_workers.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("legacy_schedule_id", name="uq_core_schedule_legacy"),
        )
        op.create_index(op.f("ix_core_schedule_blocks_booking_id"), "core_schedule_blocks", ["booking_id"], unique=False)
        op.create_index(op.f("ix_core_schedule_blocks_company_id"), "core_schedule_blocks", ["company_id"], unique=False)
        op.create_index(op.f("ix_core_schedule_blocks_ends_at"), "core_schedule_blocks", ["ends_at"], unique=False)
        op.create_index(op.f("ix_core_schedule_blocks_id"), "core_schedule_blocks", ["id"], unique=False)
        op.create_index(op.f("ix_core_schedule_blocks_legacy_schedule_id"), "core_schedule_blocks", ["legacy_schedule_id"], unique=False)
        op.create_index(op.f("ix_core_schedule_blocks_location_id"), "core_schedule_blocks", ["location_id"], unique=False)
        op.create_index(op.f("ix_core_schedule_blocks_resource_id"), "core_schedule_blocks", ["resource_id"], unique=False)
        op.create_index(op.f("ix_core_schedule_blocks_starts_at"), "core_schedule_blocks", ["starts_at"], unique=False)
        op.create_index(op.f("ix_core_schedule_blocks_status"), "core_schedule_blocks", ["status"], unique=False)
        op.create_index(op.f("ix_core_schedule_blocks_worker_id"), "core_schedule_blocks", ["worker_id"], unique=False)


def downgrade() -> None:
    """Remove tabelas de scheduling Sprint 2."""
    op.drop_index(op.f("ix_core_schedule_blocks_worker_id"), table_name="core_schedule_blocks")
    op.drop_index(op.f("ix_core_schedule_blocks_status"), table_name="core_schedule_blocks")
    op.drop_index(op.f("ix_core_schedule_blocks_starts_at"), table_name="core_schedule_blocks")
    op.drop_index(op.f("ix_core_schedule_blocks_resource_id"), table_name="core_schedule_blocks")
    op.drop_index(op.f("ix_core_schedule_blocks_location_id"), table_name="core_schedule_blocks")
    op.drop_index(op.f("ix_core_schedule_blocks_legacy_schedule_id"), table_name="core_schedule_blocks")
    op.drop_index(op.f("ix_core_schedule_blocks_id"), table_name="core_schedule_blocks")
    op.drop_index(op.f("ix_core_schedule_blocks_ends_at"), table_name="core_schedule_blocks")
    op.drop_index(op.f("ix_core_schedule_blocks_company_id"), table_name="core_schedule_blocks")
    op.drop_index(op.f("ix_core_schedule_blocks_booking_id"), table_name="core_schedule_blocks")
    op.drop_table("core_schedule_blocks")
    op.drop_index(op.f("ix_core_resources_slug"), table_name="core_resources")
    op.drop_index(op.f("ix_core_resources_location_id"), table_name="core_resources")
    op.drop_index(op.f("ix_core_resources_id"), table_name="core_resources")
    op.drop_index(op.f("ix_core_resources_company_id"), table_name="core_resources")
    op.drop_table("core_resources")
    op.drop_index(op.f("ix_core_workers_user_id"), table_name="core_workers")
    op.drop_index(op.f("ix_core_workers_id"), table_name="core_workers")
    op.drop_index(op.f("ix_core_workers_company_id"), table_name="core_workers")
    op.drop_table("core_workers")
    op.drop_index(op.f("ix_core_locations_slug"), table_name="core_locations")
    op.drop_index(op.f("ix_core_locations_name"), table_name="core_locations")
    op.drop_index(op.f("ix_core_locations_id"), table_name="core_locations")
    op.drop_index(op.f("ix_core_locations_company_id"), table_name="core_locations")
    op.drop_table("core_locations")
