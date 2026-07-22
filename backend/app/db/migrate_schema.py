"""
Migração do schema SQLite para alinhar colunas com os models SQLAlchemy.
"""
import sqlite3
from pathlib import Path
from app.core.config import settings


def _get_db_path() -> str:
    """Retorna o caminho absoluto do arquivo SQLite."""
    return settings.DATABASE_URL.replace("sqlite:///", "")


def _add_column_if_missing(cursor: sqlite3.Cursor, table: str, column: str, definition: str) -> None:
    """
    Adiciona uma coluna na tabela se ela ainda não existir.

    Args:
        cursor: Cursor SQLite ativo.
        table: Nome da tabela.
        column: Nome da coluna.
        definition: Definição SQL da coluna (ex: 'updated_at DATETIME').
    """
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        print(f"✅ Coluna '{column}' adicionada em '{table}'")


def migrate_schema() -> None:
    """
    Aplica migrações incrementais no banco SQLite existente.

    Returns:
        None
    """
    db_path = _get_db_path()
    if not Path(db_path).exists():
        print(f"❌ Banco não encontrado: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        _add_column_if_missing(cursor, "financeiro", "updated_at", "DATETIME")
        _add_column_if_missing(cursor, "agendamentos", "google_calendar_event_id", "TEXT")
        _add_column_if_missing(cursor, "agendamentos", "comprovante_url", "TEXT")
        _add_column_if_missing(cursor, "agendamentos", "service_image_id", "INTEGER")
        _add_column_if_missing(cursor, "service_images", "valor_total", "NUMERIC(10,2)")
        _add_column_if_missing(cursor, "service_images", "valor_sinal", "NUMERIC(10,2)")
        _add_column_if_missing(cursor, "service_images", "duracao_minutos", "INTEGER")
        _add_column_if_missing(cursor, "service_images", "nome", "TEXT")
        _add_column_if_missing(cursor, "service_images", "descricao", "TEXT")
        _add_column_if_missing(cursor, "service_images", "nivel_complexidade", "VARCHAR(20)")
        _add_column_if_missing(cursor, "service_images", "percentual_sinal", "NUMERIC(5,4) DEFAULT 0.30")
        _add_column_if_missing(cursor, "service_images", "quantidade_trancas", "INTEGER")
        _add_column_if_missing(cursor, "service_images", "quantidade_cabelo", "VARCHAR(50)")
        _add_column_if_missing(cursor, "service_images", "ativo", "BOOLEAN DEFAULT 1")
        _add_column_if_missing(cursor, "agendamentos", "valor_total", "NUMERIC(10,2)")
        _add_column_if_missing(cursor, "agendamentos", "valor_sinal", "NUMERIC(10,2)")
        _add_column_if_missing(cursor, "agendamentos", "valor_restante", "NUMERIC(10,2)")
        _add_column_if_missing(cursor, "agendamentos", "status_pagamento", "VARCHAR(30) DEFAULT 'pending_payment'")
        conn.commit()
        _backfill_modelo_nomes(cursor)
        _migrar_precos_categoria_para_modelos(cursor)
        _backfill_reserva_valores(cursor)
        _migrar_fila_espera(cursor)
        _criar_agenda_dias(cursor)
        _criar_schedules(cursor)
        _criar_queue_entries(cursor)
        _estender_reservas(cursor)
        _estender_payments(cursor)
        _normalizar_status_agendamentos(cursor)
        _backfill_reservas_sem_modelo(cursor)
        _migrar_multi_tenant(cursor)
        _migrar_coreflow_plugin(cursor)
        _migrar_dlq_replay_columns(cursor)
        _migrar_r2_f1_booking_sync_columns(cursor)
        _migrar_r4_f5_booking_id_columns(cursor)
        conn.commit()
        print("✅ Schema migrado com sucesso!")
    except Exception as error:
        conn.rollback()
        print(f"❌ Erro na migração: {error}")
        raise
    finally:
        conn.close()


def _migrar_precos_categoria_para_modelos(cursor: sqlite3.Cursor) -> None:
    """
    Copia preço/duração legados da categoria para modelos que ainda não têm.

    Args:
        cursor: Cursor SQLite ativo.
    """
    cursor.execute(
        """
        UPDATE service_images
        SET valor_total = (
            SELECT t.valor_total FROM trancas t WHERE t.id = service_images.service_id
        )
        WHERE valor_total IS NULL
          AND EXISTS (
              SELECT 1 FROM trancas t
              WHERE t.id = service_images.service_id AND t.valor_total IS NOT NULL
          )
        """
    )
    cursor.execute(
        """
        UPDATE service_images
        SET duracao_minutos = (
            SELECT t.duracao_minutos FROM trancas t WHERE t.id = service_images.service_id
        )
        WHERE duracao_minutos IS NULL
          AND EXISTS (
              SELECT 1 FROM trancas t
              WHERE t.id = service_images.service_id AND t.duracao_minutos IS NOT NULL
          )
        """
    )
    cursor.execute(
        """
        UPDATE service_images
        SET percentual_sinal = 0.30
        WHERE percentual_sinal IS NULL
        """
    )
    cursor.execute(
        """
        UPDATE service_images
        SET valor_sinal = ROUND(valor_total * COALESCE(percentual_sinal, 0.30), 2)
        WHERE valor_total IS NOT NULL AND (valor_sinal IS NULL OR valor_sinal = 0)
        """
    )
    cursor.execute(
        """
        UPDATE service_images
        SET ativo = 1
        WHERE ativo IS NULL
        """
    )


def _backfill_modelo_nomes(cursor: sqlite3.Cursor) -> None:
    """
    Preenche nome padrão dos modelos existentes sem nome.

    Args:
        cursor: Cursor SQLite ativo.
    """
    cursor.execute(
        """
        UPDATE service_images
        SET nome = 'Modelo ' || ordem
        WHERE (nome IS NULL OR TRIM(nome) = '') AND deleted_at IS NULL
        """
    )


def _backfill_reserva_valores(cursor: sqlite3.Cursor) -> None:
    """
    Preenche valores de reservas antigas a partir do modelo vinculado.

    Args:
        cursor: Cursor SQLite ativo.
    """
    cursor.execute(
        """
        UPDATE agendamentos
        SET status_pagamento = CASE
            WHEN status = 'cancelado' THEN 'cancelled'
            WHEN sinal_pago = 1 THEN 'partially_paid'
            ELSE 'pending_payment'
        END
        WHERE status_pagamento IS NULL OR status_pagamento = ''
        """
    )
    cursor.execute(
        """
        UPDATE agendamentos
        SET
            valor_total = (
                SELECT si.valor_total FROM service_images si
                WHERE si.id = agendamentos.service_image_id
            ),
            valor_sinal = ROUND((
                SELECT si.valor_total FROM service_images si
                WHERE si.id = agendamentos.service_image_id
            ) * 0.30, 2),
            valor_restante = ROUND((
                SELECT si.valor_total FROM service_images si
                WHERE si.id = agendamentos.service_image_id
            ) * 0.70, 2)
        WHERE service_image_id IS NOT NULL
          AND valor_total IS NULL
          AND EXISTS (
              SELECT 1 FROM service_images si
              WHERE si.id = agendamentos.service_image_id
                AND si.valor_total IS NOT NULL
          )
        """
    )


def _migrar_fila_espera(cursor: sqlite3.Cursor) -> None:
    """
    Recria tabela fila com schema de fila de espera standalone.

    Args:
        cursor: Cursor SQLite ativo.
    """
    cursor.execute("PRAGMA table_info(fila)")
    cols = [row[1] for row in cursor.fetchall()]
    if not cols:
        return
    if "cliente_id" in cols:
        return

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS fila_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            tranca_id INTEGER NOT NULL,
            service_image_id INTEGER NOT NULL,
            data DATE NOT NULL,
            horario_desejado TIME,
            observacoes TEXT,
            mesmo_dia BOOLEAN DEFAULT 0 NOT NULL,
            posicao INTEGER NOT NULL,
            status VARCHAR(20) DEFAULT 'waiting' NOT NULL,
            agendamento_id INTEGER UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME,
            FOREIGN KEY(cliente_id) REFERENCES clientes(id),
            FOREIGN KEY(tranca_id) REFERENCES trancas(id),
            FOREIGN KEY(service_image_id) REFERENCES service_images(id),
            FOREIGN KEY(agendamento_id) REFERENCES agendamentos(id)
        )
        """
    )
    cursor.execute(
        """
        INSERT INTO fila_new (
            id, cliente_id, tranca_id, service_image_id, data,
            posicao, status, agendamento_id, created_at
        )
        SELECT
            f.id,
            a.cliente_id,
            a.tranca_id,
            COALESCE(a.service_image_id, (
                SELECT si.id FROM service_images si
                WHERE si.service_id = a.tranca_id LIMIT 1
            )),
            f.data,
            f.posicao,
            'approved',
            f.agendamento_id,
            f.created_at
        FROM fila f
        JOIN agendamentos a ON a.id = f.agendamento_id
        """
    )
    cursor.execute("DROP TABLE fila")
    cursor.execute("ALTER TABLE fila_new RENAME TO fila")
    print("✅ Tabela 'fila' migrada para fila de espera")


def _criar_agenda_dias(cursor: sqlite3.Cursor) -> None:
    """
    Cria tabela agenda_dias se não existir.

    Args:
        cursor: Cursor SQLite ativo.
    """
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS agenda_dias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data DATE NOT NULL UNIQUE,
            hora_inicio INTEGER DEFAULT 8 NOT NULL,
            minuto_inicio INTEGER DEFAULT 0 NOT NULL,
            hora_fim INTEGER DEFAULT 18 NOT NULL,
            minuto_fim INTEGER DEFAULT 0 NOT NULL,
            ativo BOOLEAN DEFAULT 1 NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME
        )
        """
    )
    print("✅ Tabela 'agenda_dias' verificada")


def _criar_schedules(cursor: sqlite3.Cursor) -> None:
    """Cria tabela schedules."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agendamento_id INTEGER NOT NULL UNIQUE,
            data DATE NOT NULL,
            inicio DATETIME NOT NULL,
            fim DATETIME NOT NULL,
            status VARCHAR(20) DEFAULT 'scheduled' NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME,
            FOREIGN KEY(agendamento_id) REFERENCES agendamentos(id)
        )
        """
    )


def _criar_queue_entries(cursor: sqlite3.Cursor) -> None:
    """Cria tabela queue_entries."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS queue_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agendamento_id INTEGER,
            cliente_id INTEGER NOT NULL,
            tranca_id INTEGER,
            service_image_id INTEGER,
            posicao INTEGER NOT NULL,
            data DATE NOT NULL,
            horario_entrada TIME,
            status VARCHAR(20) DEFAULT 'waiting' NOT NULL,
            observacoes TEXT,
            mesmo_dia INTEGER DEFAULT 0 NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME,
            FOREIGN KEY(agendamento_id) REFERENCES agendamentos(id),
            FOREIGN KEY(cliente_id) REFERENCES clientes(id)
        )
        """
    )


def _estender_reservas(cursor: sqlite3.Cursor) -> None:
    """Adiciona colunas de reserva completa."""
    _add_column_if_missing(cursor, "agendamentos", "horario_aprovado", "DATETIME")
    _add_column_if_missing(cursor, "agendamentos", "percentual_sinal", "NUMERIC(5,4) DEFAULT 0.30")
    _add_column_if_missing(cursor, "agendamentos", "motivo_rejeicao", "TEXT")
    _add_column_if_missing(cursor, "agendamentos", "horario_sugerido", "DATETIME")
    _add_column_if_missing(cursor, "agendamentos", "mensagem_reagendamento", "TEXT")
    cursor.execute(
        """
        UPDATE agendamentos SET percentual_sinal = 0.30
        WHERE percentual_sinal IS NULL
        """
    )
    cursor.execute(
        """
        UPDATE agendamentos SET status = 'pending_payment'
        WHERE status = 'pendente'
        """
    )
    cursor.execute(
        """
        UPDATE agendamentos SET status = 'approved'
        WHERE status = 'confirmado'
        """
    )
    cursor.execute(
        """
        UPDATE agendamentos SET status = 'completed'
        WHERE status = 'concluido'
        """
    )
    cursor.execute(
        """
        UPDATE agendamentos SET status = 'cancelled'
        WHERE status = 'cancelado'
        """
    )


def _estender_payments(cursor: sqlite3.Cursor) -> None:
    """Atualiza tabela payments."""
    _add_column_if_missing(cursor, "payments", "transaction_id", "TEXT")
    _add_column_if_missing(cursor, "payments", "comprovante_url", "TEXT")


def _normalizar_status_agendamentos(cursor: sqlite3.Cursor) -> None:
    """
    Converte status legados (nomes de enum em maiúsculas) para values string.

    Args:
        cursor: Cursor SQLite ativo.
    """
    status_map = {
        "CONFIRMADO": "approved",
        "confirmado": "approved",
        "PENDENTE": "pending_payment",
        "pendente": "pending_payment",
        "CANCELADO": "cancelled",
        "cancelado": "cancelled",
        "CONCLUIDO": "completed",
        "concluido": "completed",
        "PENDING_PAYMENT": "pending_payment",
        "PENDING_APPROVAL": "pending_approval",
        "WAITING_TIME_CONFIRMATION": "waiting_time_confirmation",
        "APPROVED": "approved",
        "REJECTED": "rejected",
        "IN_QUEUE": "in_queue",
        "CHECKED_IN": "checked_in",
        "IN_SERVICE": "in_service",
        "COMPLETED": "completed",
        "PAID": "paid",
        "CANCELLED": "cancelled",
        "NO_SHOW": "no_show",
    }
    for legado, valor in status_map.items():
        cursor.execute(
            "UPDATE agendamentos SET status = ? WHERE status = ?",
            (valor, legado),
        )

    pagamento_map = {
        "PENDING_PAYMENT": "pending_payment",
        "PARTIALLY_PAID": "partially_paid",
        "CONFIRMED": "confirmed",
        "CANCELLED": "cancelled",
        "PAID": "paid",
        "": "pending_payment",
    }
    for legado, valor in pagamento_map.items():
        cursor.execute(
            "UPDATE agendamentos SET status_pagamento = ? WHERE status_pagamento = ? OR status_pagamento IS NULL",
            (valor, legado),
        )
    print("✅ Status de agendamentos normalizados")


def _backfill_reservas_sem_modelo(cursor: sqlite3.Cursor) -> None:
    """
    Preenche service_image_id e valores em reservas antigas sem snapshot.

    Args:
        cursor: Cursor SQLite ativo.
    """
    cursor.execute(
        """
        UPDATE agendamentos
        SET service_image_id = (
            SELECT si.id FROM service_images si
            WHERE si.service_id = agendamentos.tranca_id
              AND si.deleted_at IS NULL
            ORDER BY si.ordem ASC
            LIMIT 1
        )
        WHERE service_image_id IS NULL
        """
    )
    cursor.execute(
        """
        UPDATE agendamentos
        SET
            valor_total = (
                SELECT si.valor_total FROM service_images si
                WHERE si.id = agendamentos.service_image_id
            ),
            valor_sinal = (
                SELECT si.valor_sinal FROM service_images si
                WHERE si.id = agendamentos.service_image_id
            ),
            valor_restante = (
                SELECT ROUND(si.valor_total - si.valor_sinal, 2)
                FROM service_images si
                WHERE si.id = agendamentos.service_image_id
            ),
            percentual_sinal = COALESCE(
                (SELECT si.percentual_sinal FROM service_images si
                 WHERE si.id = agendamentos.service_image_id),
                0.30
            )
        WHERE service_image_id IS NOT NULL
          AND (valor_total IS NULL OR valor_sinal IS NULL OR valor_restante IS NULL)
        """
    )
    print("✅ Reservas antigas vinculadas a modelos")


def _migrar_multi_tenant(cursor: sqlite3.Cursor) -> None:
    """
    Adiciona colunas company_id nas tabelas operacionais (Fase A BeautyOS).

    Args:
        cursor: Cursor SQLite ativo.
    """
    tables = (
        "trancas",
        "clientes",
        "agendamentos",
        "fila",
        "agenda_dias",
        "schedules",
        "queue_entries",
        "financeiro",
        "agent_tasks",
    )
    for table in tables:
        _add_column_if_missing(cursor, table, "company_id", "INTEGER")
    print("✅ Colunas company_id adicionadas (multi-tenant Fase A)")


def _migrar_coreflow_plugin(cursor: sqlite3.Cursor) -> None:
    """
    Adiciona plugin_id em companies (CoreFlow Sprint 0).

    Args:
        cursor: Cursor SQLite ativo.
    """
    _add_column_if_missing(cursor, "companies", "plugin_id", "VARCHAR(50) DEFAULT 'beauty'")
    cursor.execute(
        "UPDATE companies SET plugin_id = 'beauty' WHERE plugin_id IS NULL OR plugin_id = ''"
    )
    print("✅ Coluna plugin_id adicionada em companies (CoreFlow)")


def _migrar_r2_f1_booking_sync_columns(cursor: sqlite3.Cursor) -> None:
    """
    Adiciona sync_status e version em core_bookings (R2-F1 / ADR-024).

    Args:
        cursor: Cursor SQLite ativo.
    """
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='core_bookings'"
    )
    if not cursor.fetchone():
        return
    _add_column_if_missing(
        cursor, "core_bookings", "sync_status", "VARCHAR DEFAULT 'synced'"
    )
    _add_column_if_missing(cursor, "core_bookings", "version", "INTEGER DEFAULT 1")
    print("✅ Colunas sync_status/version adicionadas em core_bookings (R2-F1)")


def _migrar_r4_f5_booking_id_columns(cursor: sqlite3.Cursor) -> None:
    """
    Adiciona ``booking_id`` (FK lógica ``core_bookings.id``) em
    ``queue_entries`` e ``fila`` (R4-F5 — linkage forte QueueEntry/Fila →
    CoreBooking, espelhando ``alembic/versions/cf013_r4_f5_booking_id.py``
    para o banco SQLite local gerenciado por este script legado).

    Args:
        cursor: Cursor SQLite ativo.
    """
    _add_column_if_missing(cursor, "queue_entries", "booking_id", "INTEGER")
    _add_column_if_missing(cursor, "fila", "booking_id", "INTEGER")


def _migrar_dlq_replay_columns(cursor: sqlite3.Cursor) -> None:
    """
    Adiciona colunas de replay automático em core_event_dlq (CF-20).

    Args:
        cursor: Cursor SQLite ativo.
    """
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='core_event_dlq'"
    )
    if not cursor.fetchone():
        return
    _add_column_if_missing(cursor, "core_event_dlq", "replay_attempts", "INTEGER DEFAULT 0")
    _add_column_if_missing(cursor, "core_event_dlq", "next_replay_at", "DATETIME")
    _add_column_if_missing(cursor, "core_event_dlq", "last_replay_error", "TEXT")
    print("✅ Colunas replay DLQ adicionadas (CF-20)")


if __name__ == "__main__":
    migrate_schema()
