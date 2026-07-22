"""Revision cf016 — R4-F8 DROP físico de agendamentos."""
import sqlalchemy as sa
from alembic import op

revision = "cf016_r4_f8_drop_agendamentos"
down_revision = "cf015_r4_f7_decouple_fks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    DROP físico da tabela ``agendamentos`` (R4-F8 — ADR-024 sunset /
    RFC-003 M11+).

    R4-F7 já removeu a última FK física apontando para ``agendamentos.id``
    (sete tabelas — ``payments``, ``schedules``, ``satisfaction_surveys``,
    ``fila``, ``queue_entries``, ``financeiro``, ``notification_logs``),
    então nenhuma constraint impede o DROP nesta revisão. As colunas
    ``*.agendamento_id`` nessas tabelas permanecem ``Integer`` simples,
    apenas para leitura histórica (sem join/FK necessário).

    Idempotente: só executa o ``DROP TABLE`` se a tabela ainda existir
    (compatível com ambientes onde a migration já rodou, ou com bancos de
    teste criados via ``create_all`` a partir dos models atuais — que
    desde esta release não incluem mais ``Agendamento`` como entidade
    mapeada, então a tabela nunca chega a ser criada).

    Returns:
        None.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "agendamentos" in inspector.get_table_names():
        op.drop_table("agendamentos")


def downgrade() -> None:
    """
    Recria um stub mínimo de ``agendamentos`` para permitir rollback.

    Não é uma restauração completa dos dados (o DROP físico é destrutivo
    e o rollback de schema não recupera linhas apagadas) — apenas recria
    a tabela com o schema mínimo necessário para que revisões anteriores
    (que ainda referenciam ``agendamentos`` em código, caso o rollback do
    código-fonte também aconteça) voltem a funcionar sem erro de "tabela
    inexistente". Uso esperado: apenas em rollback de emergência,
    seguido de restauração de backup se os dados históricos forem
    necessários.

    Returns:
        None.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "agendamentos" in inspector.get_table_names():
        return

    op.create_table(
        "agendamentos",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("company_id", sa.Integer(), nullable=True, index=True),
        sa.Column("cliente_id", sa.Integer(), nullable=False, index=True),
        sa.Column("tranca_id", sa.Integer(), nullable=False, index=True),
        sa.Column("service_image_id", sa.Integer(), nullable=True, index=True),
        sa.Column("data_hora", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("horario_aprovado", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sinal_pago", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("valor_total", sa.Numeric(10, 2), nullable=True),
        sa.Column("percentual_sinal", sa.Numeric(5, 4), nullable=True),
        sa.Column("valor_sinal", sa.Numeric(10, 2), nullable=True),
        sa.Column("valor_restante", sa.Numeric(10, 2), nullable=True),
        sa.Column("status_pagamento", sa.String(30), nullable=True),
        sa.Column("comprovante_url", sa.String(255), nullable=True),
        sa.Column("status", sa.String(30), nullable=True, index=True),
        sa.Column("observacoes", sa.String(255), nullable=True),
        sa.Column("motivo_rejeicao", sa.Text(), nullable=True),
        sa.Column("horario_sugerido", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mensagem_reagendamento", sa.Text(), nullable=True),
        sa.Column("google_calendar_event_id", sa.String(255), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
