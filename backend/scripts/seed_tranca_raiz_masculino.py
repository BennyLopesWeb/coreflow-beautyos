#!/usr/bin/env python3
"""
Cadastra a trança Raiz masculino no catálogo.

Uso:
    python scripts/seed_tranca_raiz_masculino.py
"""
import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.models.tranca import Tranca


def seed_tranca_raiz_masculino() -> Tranca:
    """
    Cria ou atualiza a trança Raiz masculino com imagem e descrição do catálogo.

    Returns:
        Instância Tranca persistida no banco.
    """
    imagem_url = "http://localhost:8000/static/trancas/tranca-raiz-masculino.png"
    db = SessionLocal()
    try:
        tranca = db.query(Tranca).filter(
            Tranca.nome.ilike("trança raiz masculino%"),
            Tranca.deleted_at.is_(None),
        ).first()

        dados = {
            "nome": "Trança Raiz Masculino",
            "descricao": (
                "Trança raiz (nagô) masculina com cornrows no topo, padrão geométrico "
                "com cruzamentos, laterais com fade e acabamento com brilho e definição."
            ),
            "duracao_minutos": 90,
            "valor_total": Decimal("80.00"),
            "valor_sinal": Decimal("30.00"),
            "imagens": [imagem_url],
            "ativo": True,
        }

        if tranca:
            for key, value in dados.items():
                setattr(tranca, key, value)
            action = "atualizada"
        else:
            tranca = Tranca(**dados)
            db.add(tranca)
            action = "cadastrada"

        db.commit()
        db.refresh(tranca)
        print(f"✅ Trança Raiz Masculino {action}: id={tranca.id} imagem={imagem_url}")
        return tranca
    finally:
        db.close()


if __name__ == "__main__":
    seed_tranca_raiz_masculino()
