"""Revision cf014 — R4-F6 bridge Payment -> booking_id (core)."""
import sqlalchemy as sa
from alembic import op

revision = "cf014_r4_f6_payment_booking_id"
down_revision = "cf013_r4_f5_booking_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Torna ``payments.agendamento_id`` opcional e adiciona ``payments.booking_id``
    (FK nullable ``core_bookings.id``, indexada) — R4-F6 bridge Payment→booking_id
    (ADR-024 sunset / RFC-003 M10). Pagamentos de bookings core-only (sem
    ``Agendamento`` associado) passam a poder ser vinculados diretamente ao
    booking via ``booking_id``, sem depender de ``agendamento_id``.

    Idempotente: pula alterações já aplicadas (compatível com ``create_all``
    em testes, onde o model já nasce com ``agendamento_id`` nullable e
    ``booking_id`` presente). Usa ``batch_alter_table`` (``render_as_batch``
    no ``env.py``) para suportar SQLite, que não tem ``ALTER COLUMN`` nativo.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "payments" not in inspector.get_table_names():
        return

    existing_cols = {c["name"]: c for c in inspector.get_columns("payments")}
    precisa_nullable = (
        "agendamento_id" in existing_cols
        and existing_cols["agendamento_id"]["nullable"] is False
    )
    precisa_booking_id = "booking_id" not in existing_cols

    if precisa_nullable or precisa_booking_id:
        with op.batch_alter_table("payments") as batch_op:
            if precisa_nullable:
                batch_op.alter_column(
                    "agendamento_id",
                    existing_type=sa.Integer(),
                    nullable=True,
                )
            if precisa_booking_id:
                batch_op.add_column(
                    sa.Column(
                        "booking_id",
                        sa.Integer(),
                        sa.ForeignKey(
                            "core_bookings.id",
                            name="fk_payments_booking_id_core_bookings",
                        ),
                        nullable=True,
                    ),
                )

    if precisa_booking_id:
        inspector = sa.inspect(bind)
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("payments")}
        if op.f("ix_payments_booking_id") not in existing_indexes:
            op.create_index(
                op.f("ix_payments_booking_id"), "payments", ["booking_id"], unique=False
            )


def downgrade() -> None:
    """Remove ``booking_id`` de ``payments`` e reverte ``agendamento_id`` para NOT NULL."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "payments" not in inspector.get_table_names():
        return

    existing_cols = {c["name"] for c in inspector.get_columns("payments")}
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("payments")}

    if op.f("ix_payments_booking_id") in existing_indexes:
        op.drop_index(op.f("ix_payments_booking_id"), table_name="payments")

    with op.batch_alter_table("payments") as batch_op:
        if "booking_id" in existing_cols:
            batch_op.drop_column("booking_id")
        batch_op.alter_column(
            "agendamento_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
