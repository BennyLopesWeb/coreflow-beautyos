"""Revision cf013 — R4-F5 booking_id em queue_entries/fila."""
import sqlalchemy as sa
from alembic import op

revision = "cf013_r4_f5_booking_id"
down_revision = "cf012_r2_f1b_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Adiciona ``booking_id`` (FK nullable ``core_bookings.id``, indexada) em
    ``queue_entries`` e ``fila`` (R4-F5 — linkage forte QueueEntry/Fila →
    CoreBooking, substituindo dedupe por atributos compostos usado até
    R4-F4).

    Idempotente: pula colunas/índices já existentes (compatível com
    ``create_all`` em testes).
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "queue_entries" in inspector.get_table_names():
        existing_cols = {c["name"] for c in inspector.get_columns("queue_entries")}
        if "booking_id" not in existing_cols:
            op.add_column(
                "queue_entries",
                sa.Column("booking_id", sa.Integer(), sa.ForeignKey("core_bookings.id"), nullable=True),
            )
            op.create_index(
                op.f("ix_queue_entries_booking_id"), "queue_entries", ["booking_id"], unique=False
            )

    if "fila" in inspector.get_table_names():
        existing_cols = {c["name"] for c in inspector.get_columns("fila")}
        if "booking_id" not in existing_cols:
            op.add_column(
                "fila",
                sa.Column("booking_id", sa.Integer(), sa.ForeignKey("core_bookings.id"), nullable=True),
            )
            op.create_index(op.f("ix_fila_booking_id"), "fila", ["booking_id"], unique=False)


def downgrade() -> None:
    """Remove ``booking_id`` de ``queue_entries`` e ``fila``."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "fila" in inspector.get_table_names():
        existing_cols = {c["name"] for c in inspector.get_columns("fila")}
        if "booking_id" in existing_cols:
            op.drop_index(op.f("ix_fila_booking_id"), table_name="fila")
            op.drop_column("fila", "booking_id")

    if "queue_entries" in inspector.get_table_names():
        existing_cols = {c["name"] for c in inspector.get_columns("queue_entries")}
        if "booking_id" in existing_cols:
            op.drop_index(op.f("ix_queue_entries_booking_id"), table_name="queue_entries")
            op.drop_column("queue_entries", "booking_id")
