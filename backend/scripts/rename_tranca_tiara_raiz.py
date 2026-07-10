#!/usr/bin/env python3
"""
Renomeia Twist Senegalese G → Trança Tiara Raiz e atualiza imagem/slug.

Uso:
    python scripts/rename_tranca_tiara_raiz.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.models.tranca import Tranca
from app.models.service_image import ServiceImage
from app.services.service_image_service import ServiceImageService
from app.utils.tranca_imagens import STATIC_TRANCAS

BASE_URL = "http://localhost:8000"
NOME_ANTIGO = "Twist Senegalese G"
NOME_NOVO = "Trança Tiara Raiz"
ARQUIVO_ANTIGO = "twist-senegalese-g.png"
ARQUIVO_NOVO = "tranca-tiara-raiz.png"


def rename_tranca_tiara_raiz() -> None:
    """
    Renomeia o tipo no banco, arquivo de imagem e registros service_images.

    Returns:
        None
    """
    db = SessionLocal()
    try:
        tranca = (
            db.query(Tranca)
            .filter(
                Tranca.deleted_at.is_(None),
                Tranca.nome.in_([NOME_ANTIGO, NOME_NOVO]),
            )
            .first()
        )

        if not tranca:
            tranca = (
                db.query(Tranca)
                .filter(
                    Tranca.deleted_at.is_(None),
                    Tranca.nome.ilike("%twist senegalese g%"),
                )
                .first()
            )

        if not tranca:
            print(f"❌ Trança '{NOME_ANTIGO}' não encontrada.")
            return

        url_nova = f"{BASE_URL.rstrip('/')}/static/trancas/{ARQUIVO_NOVO}"
        url_antiga = f"{BASE_URL.rstrip('/')}/static/trancas/{ARQUIVO_ANTIGO}"

        origem = STATIC_TRANCAS / ARQUIVO_ANTIGO
        destino = STATIC_TRANCAS / ARQUIVO_NOVO
        if origem.is_file() and not destino.is_file():
            origem.rename(destino)
            print(f"✅ Arquivo renomeado: {ARQUIVO_ANTIGO} → {ARQUIVO_NOVO}")
        elif destino.is_file():
            print(f"ℹ️  Arquivo já existe: {ARQUIVO_NOVO}")

        tranca.nome = NOME_NOVO
        tranca.descricao = (
            "Trança tiara raiz com acabamento uniforme, volumoso e durável. "
            "Estilo elegante com raiz bem definida."
        )
        imagens = tranca.imagens or []
        if isinstance(imagens, str):
            import json
            try:
                imagens = json.loads(imagens)
            except json.JSONDecodeError:
                imagens = []
        tranca.imagens = [
            url_nova if u.endswith(ARQUIVO_ANTIGO) or u == url_antiga else u
            for u in imagens
        ] or [url_nova]

        db.commit()
        db.refresh(tranca)

        imagens_db = (
            db.query(ServiceImage)
            .filter(
                ServiceImage.service_id == tranca.id,
                ServiceImage.deleted_at.is_(None),
            )
            .all()
        )
        for img in imagens_db:
            if ARQUIVO_ANTIGO in img.url or img.url == url_antiga:
                img.url = url_nova

        db.commit()
        ServiceImageService(db).sincronizar_da_tranca(tranca.id)

        print(f"✅ Renomeado: id={tranca.id} → '{NOME_NOVO}' imagem={url_nova}")
    finally:
        db.close()


if __name__ == "__main__":
    rename_tranca_tiara_raiz()
