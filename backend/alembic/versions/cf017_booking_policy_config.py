"""Revision cf017 — booking_policy_config + booking_policy_audit (FIX-CONFIG-01)."""
import sqlalchemy as sa
from alembic import op

revision = "cf017_booking_policy_config"
down_revision = "cf016_r4_f8_drop_agendamentos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Cria tabelas de override e auditoria de políticas de booking.

    Idempotente: só cria se a tabela ainda não existir.
    Não altera bookings, payments nem dados financeiros.

    Returns:
        None.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "booking_policy_config" not in tables:
        op.create_table(
            "booking_policy_config",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("policy_json", sa.JSON(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "company_id", name="uq_booking_policy_config_company"
            ),
        )
        op.create_index(
            op.f("ix_booking_policy_config_id"),
            "booking_policy_config",
            ["id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_booking_policy_config_company_id"),
            "booking_policy_config",
            ["company_id"],
            unique=True,
        )

    if "booking_policy_audit" not in tables:
        op.create_table(
            "booking_policy_audit",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("actor_user_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(length=64), nullable=False),
            sa.Column("before_json", sa.JSON(), nullable=True),
            sa.Column("after_json", sa.JSON(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_booking_policy_audit_id"),
            "booking_policy_audit",
            ["id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_booking_policy_audit_company_id"),
            "booking_policy_audit",
            ["company_id"],
            unique=False,
        )


def downgrade() -> None:
    """
    Remove tabelas de política de booking (rollback funcional).

    Returns:
        None.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "booking_policy_audit" in tables:
        op.drop_index(
            op.f("ix_booking_policy_audit_company_id"),
            table_name="booking_policy_audit",
        )
        op.drop_index(
            op.f("ix_booking_policy_audit_id"),
            table_name="booking_policy_audit",
        )
        op.drop_table("booking_policy_audit")

    if "booking_policy_config" in tables:
        op.drop_index(
            op.f("ix_booking_policy_config_company_id"),
            table_name="booking_policy_config",
        )
        op.drop_index(
            op.f("ix_booking_policy_config_id"),
            table_name="booking_policy_config",
        )
        op.drop_table("booking_policy_config")
