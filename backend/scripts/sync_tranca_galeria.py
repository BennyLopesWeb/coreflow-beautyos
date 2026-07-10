#!/usr/bin/env python3
"""
Sincroniza service_images a partir do campo imagens[] de cada trança.
Não importa mais todas as fotos do disco automaticamente.

Uso:
    python scripts/sync_tranca_galeria.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.models.tranca import Tranca
from app.services.tranca_service import TrancaService
from app.services.service_image_service import ServiceImageService


def sync_galeria() -> None:
    """
    Ressincroniza service_images a partir de tranca.imagens (sem varrer disco).

    Returns:
        None
    """
    db = SessionLocal()
    service = TrancaService(db)
    image_service = ServiceImageService(db)
    try:
        trancas = db.query(Tranca).filter(Tranca.deleted_at.is_(None)).all()
        for tranca in trancas:
            antes = len(service.normalizar_imagens(tranca.imagens))
            image_service.sincronizar_da_tranca(tranca.id)
            depois = len(image_service.listar_por_tranca(tranca.id))
            print(f"✅ {tranca.nome}: {antes} URL(s) → {depois} foto(s) com ID")
    finally:
        db.close()


if __name__ == "__main__":
    sync_galeria()
