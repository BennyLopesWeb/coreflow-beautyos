#!/usr/bin/env python3
"""
Atualiza Twist Senegalese → Twist Senegalese P e cadastra Trança Tiara Raiz.

Uso:
    python scripts/seed_tranca_twist_senegalese_variants.py
"""
import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.models.tranca import Tranca


def seed_twist_senegalese_variants() -> None:
    """
    Renomeia a trança existente para Twist Senegalese P e cria Trança Tiara Raiz.

    Returns:
        None
    """
    db = SessionLocal()
    try:
        # Renomear Twist Senegalese existente → Twist Senegalese P
        tranca_p = db.query(Tranca).filter(
            Tranca.nome.ilike("twist senegalese%"),
            Tranca.deleted_at.is_(None),
        ).first()

        imagem_p = "http://localhost:8000/static/trancas/twist-senegalese.png"
        dados_p = {
            "nome": "Twist Senegalese P",
            "descricao": (
                "Twist senegalese finos (P) com efeito ombré: raiz escura, mechas loiras "
                "e fios castanhos. Acabamento uniforme, brilhante e durável."
            ),
            "duracao_minutos": 150,
            "valor_total": Decimal("120.00"),
            "valor_sinal": Decimal("40.00"),
            "imagens": [imagem_p],
            "ativo": True,
        }

        if tranca_p:
            for key, value in dados_p.items():
                setattr(tranca_p, key, value)
            print(f"✅ Twist Senegalese P atualizada: id={tranca_p.id}")
        else:
            tranca_p = Tranca(**dados_p)
            db.add(tranca_p)
            db.commit()
            db.refresh(tranca_p)
            print(f"✅ Twist Senegalese P criada: id={tranca_p.id}")

        # Cadastrar Trança Tiara Raiz (antes Twist Senegalese G)
        tranca_g = db.query(Tranca).filter(
            Tranca.nome.in_(["Twist Senegalese G", "Trança Tiara Raiz"]),
            Tranca.deleted_at.is_(None),
        ).first()

        imagem_g = "http://localhost:8000/static/trancas/tranca-tiara-raiz.png"
        dados_g = {
            "nome": "Trança Tiara Raiz",
            "descricao": (
                "Trança tiara raiz com acabamento uniforme, volumoso e durável. "
                "Estilo elegante com raiz bem definida."
            ),
            "duracao_minutos": 180,
            "valor_total": Decimal("150.00"),
            "valor_sinal": Decimal("50.00"),
            "imagens": [imagem_g],
            "ativo": True,
        }

        if tranca_g:
            for key, value in dados_g.items():
                setattr(tranca_g, key, value)
            action_g = "atualizada"
        else:
            tranca_g = Tranca(**dados_g)
            db.add(tranca_g)
            action_g = "cadastrada"

        db.commit()
        db.refresh(tranca_g)
        print(f"✅ Trança Tiara Raiz {action_g}: id={tranca_g.id} imagem={imagem_g}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_twist_senegalese_variants()
