"""Revision cf018 — snapshot de política de ativação em core_bookings."""
import sqlalchemy as sa
from alembic import op

revision = "cf018_booking_activation_snapshot"
down_revision = "cf017_booking_policy_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Adiciona colunas de snapshot de ativação em ``core_bookings``.

    Idempotente: só cria a coluna se ainda não existir.
    Não faz backfill — bookings legados permanecem NULL (regra legada).

    Returns:
        None.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if "core_bookings" not in tables:
        return

    columns = {c["name"] for c in inspector.get_columns("core_bookings")}
    if "minimum_activation_cents" not in columns:
        op.add_column(
            "core_bookings",
            sa.Column("minimum_activation_cents", sa.Integer(), nullable=True),
        )
    if "activation_policy_snapshot" not in columns:
        op.add_column(
            "core_bookings",
            sa.Column("activation_policy_snapshot", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    """
    Remove colunas de snapshot de ativação.

    Returns:
        None.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if "core_bookings" not in tables:
        return
    columns = {c["name"] for c in inspector.get_columns("core_bookings")}
    if "activation_policy_snapshot" in columns:
        op.drop_column("core_bookings", "activation_policy_snapshot")
    if "minimum_activation_cents" in columns:
        op.drop_column("core_bookings", "minimum_activation_cents")
