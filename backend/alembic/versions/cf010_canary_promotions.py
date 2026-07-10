"""Revision cf010 — core_canary_promotions (CF-25 canary rollback persist)."""
from alembic import op
import sqlalchemy as sa

revision = "cf010_canary_promotions"
down_revision = "cf009_device_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Cria tabela core_canary_promotions para rollback canary persistente."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "core_canary_promotions" not in tables:
        op.create_table(
            "core_canary_promotions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("plugin_id", sa.String(), nullable=False),
            sa.Column("segment", sa.String(), nullable=False),
            sa.Column("previous_branch", sa.String(), nullable=False),
            sa.Column("promoted_branch", sa.String(), nullable=False),
            sa.Column("production_channel", sa.String(), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("rolled_back_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=True,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("plugin_id", "segment", name="uq_canary_promotion_plugin_segment"),
        )
        op.create_index(
            op.f("ix_core_canary_promotions_id"), "core_canary_promotions", ["id"], unique=False
        )
        op.create_index(
            op.f("ix_core_canary_promotions_plugin_id"),
            "core_canary_promotions",
            ["plugin_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_core_canary_promotions_segment"),
            "core_canary_promotions",
            ["segment"],
            unique=False,
        )
        op.create_index(
            op.f("ix_core_canary_promotions_active"),
            "core_canary_promotions",
            ["active"],
            unique=False,
        )


def downgrade() -> None:
    """Remove core_canary_promotions."""
    op.drop_index(op.f("ix_core_canary_promotions_active"), table_name="core_canary_promotions")
    op.drop_index(op.f("ix_core_canary_promotions_segment"), table_name="core_canary_promotions")
    op.drop_index(op.f("ix_core_canary_promotions_plugin_id"), table_name="core_canary_promotions")
    op.drop_index(op.f("ix_core_canary_promotions_id"), table_name="core_canary_promotions")
    op.drop_table("core_canary_promotions")
