#!/usr/bin/env python3
"""
Cadastra a trança Bob Chanel no catálogo.

Uso:
    python scripts/seed_tranca_bob_chanel.py
"""
import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.models.tranca import Tranca


def seed_tranca_bob_chanel() -> Tranca:
    """
    Cria ou atualiza a trança Bob Chanel com imagem e descrição do catálogo.

    Returns:
        Instância Tranca persistida no banco.
    """
    imagem_url = "http://localhost:8000/static/trancas/bob-chanel.png"
    db = SessionLocal()
    try:
        tranca = db.query(Tranca).filter(
            Tranca.nome.ilike("bob chanel%"),
            Tranca.deleted_at.is_(None),
        ).first()

        dados = {
            "nome": "Bob Chanel",
            "descricao": (
                "Box braids individuais no corte bob Chanel: comprimento no queixo, "
                "pontas curvadas para dentro, parting lateral e mechas loiras de destaque."
            ),
            "duracao_minutos": 150,
            "valor_total": Decimal("140.00"),
            "valor_sinal": Decimal("50.00"),
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
        print(f"✅ Trança Bob Chanel {action}: id={tranca.id} imagem={imagem_url}")
        return tranca
    finally:
        db.close()


if __name__ == "__main__":
    seed_tranca_bob_chanel()
