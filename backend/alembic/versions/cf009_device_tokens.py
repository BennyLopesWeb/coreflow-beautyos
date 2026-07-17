"""Revision cf009 — core_device_tokens (Sprint 12 push mobile)."""
from alembic import op
import sqlalchemy as sa

revision = "cf009_device_tokens"
down_revision = "cf008_assets_inventory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Cria tabela core_device_tokens para push Expo."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "core_device_tokens" not in tables:
        op.create_table(
            "core_device_tokens",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("expo_push_token", sa.String(255), nullable=False),
            sa.Column("platform", sa.String(255), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("expo_push_token", name="uq_core_device_tokens_expo_push_token"),
        )
        op.create_index(op.f("ix_core_device_tokens_company_id"), "core_device_tokens", ["company_id"], unique=False)
        op.create_index(op.f("ix_core_device_tokens_id"), "core_device_tokens", ["id"], unique=False)
        op.create_index(op.f("ix_core_device_tokens_user_id"), "core_device_tokens", ["user_id"], unique=False)


def downgrade() -> None:
    """Remove core_device_tokens."""
    op.drop_index(op.f("ix_core_device_tokens_user_id"), table_name="core_device_tokens")
    op.drop_index(op.f("ix_core_device_tokens_id"), table_name="core_device_tokens")
    op.drop_index(op.f("ix_core_device_tokens_company_id"), table_name="core_device_tokens")
    op.drop_table("core_device_tokens")
