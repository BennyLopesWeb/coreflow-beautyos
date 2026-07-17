"""Revision cf011 — R2-F1 booking sync_status + version."""
import sqlalchemy as sa
from alembic import op

revision = "cf011_r2_f1_booking_sync"
down_revision = "cf010_canary_promotions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Adiciona sync_status e version em core_bookings (ADR-024).

    Idempotente para SQLite/tests que usam create_all.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "core_bookings" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("core_bookings")}
    if "sync_status" not in columns:
        op.add_column(
            "core_bookings",
            sa.Column("sync_status", sa.String(255), nullable=False, server_default="synced"),
        )
    if "version" not in columns:
        op.add_column(
            "core_bookings",
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        )


def downgrade() -> None:
    """Remove colunas R2-F1 de core_bookings."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "core_bookings" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("core_bookings")}
    if "version" in columns:
        op.drop_column("core_bookings", "version")
    if "sync_status" in columns:
        op.drop_column("core_bookings", "sync_status")
