#!/usr/bin/env python3
"""
Cadastra ou atualiza a trança Twist Senegalese no catálogo.

Uso:
    python scripts/seed_tranca_twist_senegalese.py
"""
import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.models.tranca import Tranca


def seed_tranca_twist_senegalese() -> Tranca:
    """
    Cria ou atualiza a Twist Senegalese com imagem e descrição do catálogo.

    Returns:
        Instância Tranca persistida no banco.
    """
    imagem_url = "http://localhost:8000/static/trancas/twist-senegalese.png"
    db = SessionLocal()
    try:
        tranca = db.query(Tranca).filter(
            Tranca.nome.ilike("twist senegalese%"),
            Tranca.deleted_at.is_(None),
        ).first()

        dados = {
            "nome": "Twist Senegalese",
            "descricao": (
                "Twist senegalese longos com efeito ombré: raiz escura, mechas loiras "
                "e fios castanhos. Acabamento uniforme, brilhante e durável."
            ),
            "duracao_minutos": 150,
            "valor_total": Decimal("120.00"),
            "valor_sinal": Decimal("40.00"),
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
        print(f"✅ Twist Senegalese {action}: id={tranca.id} imagem={imagem_url}")
        return tranca
    finally:
        db.close()


if __name__ == "__main__":
    seed_tranca_twist_senegalese()
