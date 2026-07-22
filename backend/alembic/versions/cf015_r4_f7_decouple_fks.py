"""Revision cf015 — R4-F7 decouple physical FKs to agendamentos."""
import sqlalchemy as sa
from alembic import op

revision = "cf015_r4_f7_decouple_fks"
down_revision = "cf014_r4_f6_payment_booking_id"
branch_labels = None
depends_on = None


# Tabelas que só perdem a FK física para ``agendamentos.id`` nesta revisão —
# ``agendamento_id`` já é nullable (ou opcional desde a criação) e permanece
# como ``Integer`` simples (histórico), sem constraint física.
_TABELAS_APENAS_DROP_FK = (
    "payments",
    "fila",
    "queue_entries",
    "financeiro",
    "notification_logs",
)

# Tabelas que, além do drop de FK, ganham ``agendamento_id`` nullable (drop
# do NOT NULL físico) + ``booking_id`` (Integer, FK nullable indexada para
# ``core_bookings.id``) — bridge equivalente ao feito em ``payments`` no
# R4-F6 (``cf014_r4_f6_payment_booking_id``).
_TABELAS_COM_BOOKING_ID = ("schedules", "satisfaction_surveys")


def _fk_constraints_para(tabela: sa.Table, tabela_referenciada: str) -> list:
    """
    Filtra as ``ForeignKeyConstraint`` de ``tabela`` que referenciam
    ``tabela_referenciada``.

    Args:
        tabela: ``sa.Table`` refletida (ou em construção) a inspecionar.
        tabela_referenciada: Nome da tabela alvo (ex.: ``"agendamentos"``).

    Returns:
        Lista de ``ForeignKeyConstraint`` cujo ``referred_table.name``
        casa com ``tabela_referenciada``.
    """
    return [
        c
        for c in list(tabela.constraints)
        if isinstance(c, sa.ForeignKeyConstraint)
        and c.referred_table.name == tabela_referenciada
    ]


def _recriar_tabela_sqlite(
    bind,
    table_name: str,
    *,
    remover_fk_para: str = "agendamentos",
    tornar_nullable: tuple = (),
    tornar_not_null: tuple = (),
    readicionar_fk_para: str = None,
) -> None:
    """
    Recria uma tabela SQLite via ``batch_alter_table(copy_from=..., recreate="always")``.

    SQLite reflete ``ForeignKeyConstraint`` sem nome (``get_foreign_keys``
    retorna ``name=None``), então ``batch_op.drop_constraint`` por nome não
    é viável (Alembic exige nome). A estratégia usada aqui é reconstruir a
    tabela a partir da definição refletida (``sa.Table(..., autoload_with=bind)``),
    removendo apenas as ``ForeignKeyConstraint``/``ForeignKey`` cujo
    ``referred_table`` casa com ``remover_fk_para`` (mantendo intactas todas
    as demais colunas, índices e constraints), ajustando nullable onde
    solicitado. Também suporta o caminho inverso (``downgrade``): readicionar
    uma FK removida via ``readicionar_fk_para`` (usado para round-trip
    ``upgrade``/``downgrade``).

    Args:
        bind: Conexão SQLAlchemy ativa (``op.get_bind()``).
        table_name: Nome da tabela a recriar.
        remover_fk_para: Nome da tabela referenciada cuja(s) FK(s) devem ser
            removidas de ``table_name`` (``None`` para não remover nenhuma).
        tornar_nullable: Nomes de colunas a marcar ``nullable=True``.
        tornar_not_null: Nomes de colunas a marcar ``nullable=False``
            (usado no downgrade, para reverter o ``tornar_nullable`` do
            upgrade).
        readicionar_fk_para: Nome da tabela para a qual uma
            ``ForeignKeyConstraint`` deve ser readicionada na(s) coluna(s)
            de ``tornar_not_null`` (usado no downgrade — assume a mesma
            coluna, ex.: ``agendamento_id`` → ``agendamentos.id``).

    Returns:
        None.
    """
    meta = sa.MetaData()
    tabela = sa.Table(table_name, meta, autoload_with=bind)

    if remover_fk_para:
        constraints_fk = _fk_constraints_para(tabela, remover_fk_para)
        for c in constraints_fk:
            tabela.constraints.discard(c)
        for fk in list(tabela.foreign_keys):
            if fk.constraint in constraints_fk:
                tabela.foreign_keys.discard(fk)

    for nome_coluna in tornar_nullable:
        if nome_coluna in tabela.columns:
            tabela.columns[nome_coluna].nullable = True

    for nome_coluna in tornar_not_null:
        if nome_coluna in tabela.columns:
            tabela.columns[nome_coluna].nullable = False

    if readicionar_fk_para:
        for nome_coluna in tornar_not_null:
            if nome_coluna in tabela.columns:
                tabela.append_constraint(
                    sa.ForeignKeyConstraint(
                        [nome_coluna], [f"{readicionar_fk_para}.id"]
                    )
                )

    with op.batch_alter_table(table_name, copy_from=tabela, recreate="always"):
        pass


def _drop_fk_para_agendamentos_outros_dialetos(
    bind, inspector, table_name: str, tornar_nullable: tuple = ()
) -> None:
    """
    Remove a FK física para ``agendamentos`` em dialetos que persistem o
    nome da constraint na reflexão (MySQL/PostgreSQL) — diferente do
    SQLite, esses bancos retornam ``name`` preenchido em
    ``inspector.get_foreign_keys``, permitindo ``drop_constraint`` direto
    sem precisar recriar a tabela inteira.

    Args:
        bind: Conexão SQLAlchemy ativa.
        inspector: ``sa.inspect(bind)`` já criado pelo chamador.
        table_name: Nome da tabela a alterar.
        tornar_nullable: Nomes de colunas a marcar ``nullable=True`` (ex.:
            ``("agendamento_id",)``).

    Returns:
        None.
    """
    fks = [
        fk
        for fk in inspector.get_foreign_keys(table_name)
        if fk.get("referred_table") == "agendamentos" and fk.get("name")
    ]
    if fks:
        with op.batch_alter_table(table_name) as batch_op:
            for fk in fks:
                batch_op.drop_constraint(fk["name"], type_="foreignkey")

    if tornar_nullable:
        existing_cols = {c["name"]: c for c in inspector.get_columns(table_name)}
        with op.batch_alter_table(table_name) as batch_op:
            for nome_coluna in tornar_nullable:
                col = existing_cols.get(nome_coluna)
                if col is not None and col["nullable"] is False:
                    batch_op.alter_column(
                        nome_coluna, existing_type=sa.Integer(), nullable=True
                    )


def _adicionar_booking_id(bind, table_name: str) -> None:
    """
    Adiciona ``booking_id`` (Integer, FK nullable ``core_bookings.id``,
    indexada) em ``table_name``, se ainda não existir. Idempotente.

    Args:
        bind: Conexão SQLAlchemy ativa.
        table_name: Nome da tabela (``schedules`` ou ``satisfaction_surveys``).

    Returns:
        None.
    """
    inspector = sa.inspect(bind)
    existing_cols = {c["name"] for c in inspector.get_columns(table_name)}
    if "booking_id" not in existing_cols:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "booking_id",
                    sa.Integer(),
                    sa.ForeignKey(
                        "core_bookings.id",
                        name=f"fk_{table_name}_booking_id_core_bookings",
                    ),
                    nullable=True,
                ),
            )

    inspector = sa.inspect(bind)
    existing_indexes = {idx["name"] for idx in inspector.get_indexes(table_name)}
    index_name = op.f(f"ix_{table_name}_booking_id")
    if index_name not in existing_indexes:
        op.create_index(index_name, table_name, ["booking_id"], unique=False)


def upgrade() -> None:
    """
    Decouple físico das FKs restantes para ``agendamentos`` (R4-F7 — ADR-024
    sunset / RFC-003 M11). Remove a constraint física ``FOREIGN KEY ...
    REFERENCES agendamentos(id)`` de sete tabelas (mantendo
    ``agendamento_id`` como ``Integer`` simples, apenas para leitura
    histórica), e adiciona ``booking_id`` (bridge para ``core_bookings.id``,
    mesmo padrão de ``payments`` no R4-F6) em ``schedules`` e
    ``satisfaction_surveys``, cujo ``agendamento_id`` também deixa de ser
    ``NOT NULL``.

    A tabela ``agendamentos`` **não é removida** — permanece necessária
    para fixtures/histórico (CF6/CF9/sync legado→core) até o DROP físico
    planejado para **R4-F8**.

    Idempotente: pula tabelas/colunas/constraints já ausentes ou já
    ajustadas (compatível com ``create_all`` em testes, onde os models já
    nascem sem a FK física). SQLite não permite ``DROP CONSTRAINT``/
    ``ALTER COLUMN`` nativos e reflete FKs sem nome — usa recriação de
    tabela via ``batch_alter_table(copy_from=..., recreate="always")``.
    Dialetos que persistem nome de constraint na reflexão (MySQL/
    PostgreSQL) usam ``drop_constraint`` direto.

    Returns:
        None.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    existing_tables = set(inspector.get_table_names())

    for table_name in _TABELAS_APENAS_DROP_FK:
        if table_name not in existing_tables:
            continue
        if is_sqlite:
            _recriar_tabela_sqlite(bind, table_name, remover_fk_para="agendamentos")
        else:
            _drop_fk_para_agendamentos_outros_dialetos(bind, inspector, table_name)
        inspector = sa.inspect(bind)

    for table_name in _TABELAS_COM_BOOKING_ID:
        if table_name not in existing_tables:
            continue

        if is_sqlite:
            _recriar_tabela_sqlite(
                bind,
                table_name,
                remover_fk_para="agendamentos",
                tornar_nullable=("agendamento_id",),
            )
        else:
            _drop_fk_para_agendamentos_outros_dialetos(
                bind, inspector, table_name, tornar_nullable=("agendamento_id",)
            )
        inspector = sa.inspect(bind)

        _adicionar_booking_id(bind, table_name)
        inspector = sa.inspect(bind)


def downgrade() -> None:
    """
    Reverte o decouple das FKs para ``agendamentos`` (R4-F7).

    Remove ``booking_id`` de ``schedules``/``satisfaction_surveys``, reverte
    ``agendamento_id`` para ``NOT NULL`` nessas duas tabelas e readiciona a
    constraint física ``FOREIGN KEY ... REFERENCES agendamentos(id)`` em
    todas as sete tabelas afetadas pelo upgrade (round-trip completo).

    Returns:
        None.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    existing_tables = set(inspector.get_table_names())

    for table_name in _TABELAS_COM_BOOKING_ID:
        if table_name not in existing_tables:
            continue

        existing_cols = {c["name"] for c in inspector.get_columns(table_name)}
        existing_indexes = {idx["name"] for idx in inspector.get_indexes(table_name)}
        index_name = op.f(f"ix_{table_name}_booking_id")
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name=table_name)
        if "booking_id" in existing_cols:
            with op.batch_alter_table(table_name) as batch_op:
                batch_op.drop_column("booking_id")
        inspector = sa.inspect(bind)

        if is_sqlite:
            _recriar_tabela_sqlite(
                bind,
                table_name,
                remover_fk_para=None,
                tornar_not_null=("agendamento_id",),
                readicionar_fk_para="agendamentos",
            )
        else:
            with op.batch_alter_table(table_name) as batch_op:
                batch_op.alter_column(
                    "agendamento_id", existing_type=sa.Integer(), nullable=False
                )
                batch_op.create_foreign_key(
                    f"fk_{table_name}_agendamento_id_agendamentos",
                    "agendamentos",
                    ["agendamento_id"],
                    ["id"],
                )
        inspector = sa.inspect(bind)

    for table_name in _TABELAS_APENAS_DROP_FK:
        if table_name not in existing_tables:
            continue

        if is_sqlite:
            meta = sa.MetaData()
            tabela = sa.Table(table_name, meta, autoload_with=bind)
            if not _fk_constraints_para(tabela, "agendamentos"):
                tabela.append_constraint(
                    sa.ForeignKeyConstraint(
                        ["agendamento_id"], ["agendamentos.id"]
                    )
                )
                with op.batch_alter_table(
                    table_name, copy_from=tabela, recreate="always"
                ):
                    pass
        else:
            with op.batch_alter_table(table_name) as batch_op:
                batch_op.create_foreign_key(
                    f"fk_{table_name}_agendamento_id_agendamentos",
                    "agendamentos",
                    ["agendamento_id"],
                    ["id"],
                )
        inspector = sa.inspect(bind)
