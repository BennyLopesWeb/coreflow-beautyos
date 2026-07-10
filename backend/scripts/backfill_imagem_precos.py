#!/usr/bin/env python3
"""
Recalcula sinal (30%) e preenche totais/duração das fotos existentes.

Uso:
    python scripts/backfill_imagem_precos.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.models.tranca import Tranca
from app.services.service_image_service import ServiceImageService


def backfill() -> None:
    """
    Sincroniza preços de todas as fotos; sinal = 30% do valor total de cada modelo.

    Returns:
        None
    """
    db = SessionLocal()
    svc = ServiceImageService(db)
    try:
        trancas = db.query(Tranca).filter(Tranca.deleted_at.is_(None)).all()
        for tranca in trancas:
            imgs = svc.sincronizar_da_tranca(tranca.id)
            print(f"✅ {tranca.nome}: {len(imgs)} foto(s) — sinal 30% recalculado")
    finally:
        db.close()


if __name__ == "__main__":
    backfill()
