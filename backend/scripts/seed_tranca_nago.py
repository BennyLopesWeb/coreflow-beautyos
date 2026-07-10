#!/usr/bin/env python3
"""
Cadastra a trança Nagô no catálogo.

Uso:
    python scripts/seed_tranca_nago.py
"""
import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.models.tranca import Tranca


def seed_tranca_nago() -> Tranca:
    """
    Cria ou atualiza a trança Nagô com imagem e descrição do catálogo.

    Returns:
        Instância Tranca persistida no banco.
    """
    imagem_url = "http://localhost:8000/static/trancas/nago.png"
    db = SessionLocal()
    try:
        tranca = db.query(Tranca).filter(
            Tranca.nome.ilike("nag%"),
            Tranca.deleted_at.is_(None),
        ).first()

        dados = {
            "nome": "Nagô",
            "descricao": (
                "Tranças nagô com raíz em cornrows, comprimento longo, "
                "pontas onduladas e detalhes dourados. Estilo elegante e durável."
            ),
            "duracao_minutos": 240,
            "valor_total": Decimal("200.00"),
            "valor_sinal": Decimal("70.00"),
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
        print(f"✅ Trança Nagô {action}: id={tranca.id} imagem={imagem_url}")
        return tranca
    finally:
        db.close()


if __name__ == "__main__":
    seed_tranca_nago()
