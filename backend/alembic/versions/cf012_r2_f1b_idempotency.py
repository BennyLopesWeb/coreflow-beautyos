"""Revision cf012 — R2-F1b idempotency_keys."""
import sqlalchemy as sa
from alembic import op

revision = "cf012_r2_f1b_idempotency"
down_revision = "cf011_r2_f1_booking_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Cria tabela idempotency_keys (ADR-031).

    Idempotente se tabela já existir (create_all em testes).
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "idempotency_keys" in inspector.get_table_names():
        return
    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("endpoint", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False, server_default="201"),
        sa.Column("response_body", sa.Text(), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key",
            "company_id",
            "endpoint",
            name="uq_idempotency_key_company_endpoint",
        ),
    )
    op.create_index(
        op.f("ix_idempotency_keys_id"), "idempotency_keys", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_idempotency_keys_idempotency_key"),
        "idempotency_keys",
        ["idempotency_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_idempotency_keys_company_id"),
        "idempotency_keys",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_idempotency_keys_booking_id"),
        "idempotency_keys",
        ["booking_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove tabela idempotency_keys."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "idempotency_keys" not in inspector.get_table_names():
        return
    op.drop_index(op.f("ix_idempotency_keys_booking_id"), table_name="idempotency_keys")
    op.drop_index(op.f("ix_idempotency_keys_company_id"), table_name="idempotency_keys")
    op.drop_index(
        op.f("ix_idempotency_keys_idempotency_key"), table_name="idempotency_keys"
    )
    op.drop_index(op.f("ix_idempotency_keys_id"), table_name="idempotency_keys")
    op.drop_table("idempotency_keys")
