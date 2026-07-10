#!/usr/bin/env python3
"""
Atualiza a imagem da trança Fulani Braids no catálogo.

Uso:
    python scripts/seed_tranca_fulani.py
"""
import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.models.tranca import Tranca


def seed_tranca_fulani() -> Tranca:
    """
    Atualiza Fulani Braids com nova imagem e descrição.

    Returns:
        Instância Tranca persistida no banco.
    """
    imagem_url = "http://localhost:8000/static/trancas/fulani-braids.png"
    db = SessionLocal()
    try:
        tranca = db.query(Tranca).filter(
            Tranca.nome.ilike("fulani%"),
            Tranca.deleted_at.is_(None),
        ).first()

        dados = {
            "nome": "Fulani Braids",
            "descricao": (
                "Tranças fulani com cornrow central, tranças laterais com miçangas "
                "douradas e prateadas, acabamento elegante e detalhes decorativos."
            ),
            "duracao_minutos": 210,
            "valor_total": Decimal("180.00"),
            "valor_sinal": Decimal("60.00"),
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
        print(f"✅ Fulani Braids {action}: id={tranca.id} imagem={imagem_url}")
        return tranca
    finally:
        db.close()


if __name__ == "__main__":
    seed_tranca_fulani()
