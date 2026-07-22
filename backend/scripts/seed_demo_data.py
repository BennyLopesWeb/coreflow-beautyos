#!/usr/bin/env python3
"""
Popula o banco com dados de demonstração para testar o frontend.

Uso:
    python scripts/seed_demo_data.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.models.tranca import Tranca
from app.models.cliente import Cliente
from app.models.financeiro import Financeiro, TipoMovimento
from datetime import datetime, timedelta


def seed_demo_data() -> None:
    """
    Cria tranças e um movimento financeiro de exemplo.

    .. deprecated:: 2.11.0-r4-f8
        Não cria mais um agendamento de exemplo — a tabela ``agendamentos``
        foi removida via DROP físico (ADR-024 sunset / RFC-003 M11+).
        Para popular uma reserva de demonstração completa, sincronize o
        catálogo (``LegacySyncService(db).sync_all()``) e use
        ``POST /v1/bookings`` (ou ``CreateBookingHandler``) — o movimento
        financeiro abaixo é criado isolado, apenas para exercitar a tela
        de financeiro.

    Returns:
        None
    """
    db = SessionLocal()
    try:
        if db.query(Tranca).count() == 0:
            trancas = [
                Tranca(
                    nome="Box Braids",
                    descricao="Tranças box braids clássicas, duráveis e versáteis.",
                    duracao_minutos=180,
                    valor_total=150.00,
                    valor_sinal=50.00,
                    imagens=[],
                    ativo=True,
                ),
                Tranca(
                    nome="Twist Senegalese P",
                    descricao="Twist senegalese finos (P) com acabamento natural.",
                    duracao_minutos=150,
                    valor_total=120.00,
                    valor_sinal=40.00,
                    imagens=[],
                    ativo=True,
                ),
                Tranca(
                    nome="Fulani Braids",
                    descricao="Tranças fulani com detalhes decorativos.",
                    duracao_minutos=210,
                    valor_total=180.00,
                    valor_sinal=60.00,
                    imagens=[],
                    ativo=True,
                ),
            ]
            db.add_all(trancas)
            db.commit()
            print(f"✅ {len(trancas)} tranças criadas")
        else:
            print("ℹ️ Tranças já existem, pulando...")

        tranca = db.query(Tranca).first()
        cliente = db.query(Cliente).first()

        if tranca and cliente and db.query(Financeiro).count() == 0:
            movimento = Financeiro(
                tipo=TipoMovimento.ENTRADA,
                descricao=f"Sinal - {tranca.nome}",
                valor=tranca.valor_sinal,
                agendamento_id=None,
                data=datetime.now(),
            )
            db.add(movimento)
            db.commit()
            print("✅ Movimento financeiro de exemplo criado")
        else:
            print("ℹ️ Movimentos financeiros já existem ou faltam trança/cliente")

    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
