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
from app.models.agendamento import Agendamento, StatusAgendamento
from app.models.financeiro import Financeiro, TipoMovimento
from datetime import datetime, timedelta


def seed_demo_data() -> None:
    """
    Cria tranças, agendamentos e movimentos financeiros de exemplo.

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

        if tranca and cliente and db.query(Agendamento).count() == 0:
            agendamento = Agendamento(
                cliente_id=cliente.id,
                tranca_id=tranca.id,
                data_hora=datetime.now() + timedelta(days=2),
                sinal_pago=True,
                status=StatusAgendamento.CONFIRMADO,
                observacoes="Cliente preferencial",
            )
            db.add(agendamento)
            db.commit()
            db.refresh(agendamento)

            movimento = Financeiro(
                tipo=TipoMovimento.ENTRADA,
                descricao=f"Sinal - {tranca.nome}",
                valor=tranca.valor_sinal,
                agendamento_id=agendamento.id,
                data=datetime.now(),
            )
            db.add(movimento)
            db.commit()
            print("✅ Agendamento e movimento financeiro de exemplo criados")
        else:
            print("ℹ️ Agendamentos já existem ou faltam trança/cliente")

    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
