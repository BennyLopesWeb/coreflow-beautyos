#!/usr/bin/env python3
"""
Corrige álbuns de fotos: cada tipo mantém apenas fotos do seu slug.

Remove fotos demo duplicadas (ex: box-braids-2/3 copiadas de outros tipos)
e ressincroniza service_images.

Uso:
    python scripts/fix_tranca_albuns.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.models.tranca import Tranca
from app.services.tranca_service import TrancaService
from app.services.service_image_service import ServiceImageService
from app.utils.tranca_slug import nome_para_slug
from app.utils.tranca_imagens import url_pertence_ao_slug, STATIC_TRANCAS

BASE_URL = "http://localhost:8000"

# Fotos demo que eram cópias de outros tipos — remover do disco
ARQUIVOS_REMOVER = [
    "box-braids-2.png",
    "box-braids-3.png",
]


def fix_albuns() -> None:
    """
    Isola álbum de cada trança e mantém só a foto principal ({slug}.png).

    Returns:
        None
    """
    for nome in ARQUIVOS_REMOVER:
        path = STATIC_TRANCAS / nome
        if path.is_file():
            path.unlink()
            print(f"🗑️  Removido arquivo duplicado: {nome}")

    db = SessionLocal()
    tranca_service = TrancaService(db)
    image_service = ServiceImageService(db)

    try:
        trancas = db.query(Tranca).filter(Tranca.deleted_at.is_(None)).all()
        for tranca in trancas:
            slug = nome_para_slug(tranca.nome)
            antes = tranca_service.normalizar_imagens(tranca.imagens)

            # Mantém só URLs cujo arquivo pertence a este slug
            filtradas = [u for u in antes if url_pertence_ao_slug(u, slug)]

            # Por enquanto: apenas foto principal escolhida para o tipo
            principal = f"{BASE_URL.rstrip('/')}/static/trancas/{slug}.png"
            arquivo_principal = STATIC_TRANCAS / f"{slug}.png"
            if arquivo_principal.is_file():
                depois = [principal]
            else:
                depois = filtradas[:1] if filtradas else []

            tranca.imagens = depois
            db.commit()
            image_service.sincronizar_da_tranca(tranca.id)

            print(
                f"✅ {tranca.nome}: {len(antes)} → {len(depois)} foto(s) "
                f"{depois if depois else '(nenhuma)'}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    fix_albuns()
