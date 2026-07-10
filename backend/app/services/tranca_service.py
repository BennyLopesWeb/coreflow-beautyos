"""
Service de Tranca (categoria)
Agrupa modelos — sem regras comerciais.
"""
from pathlib import Path
from typing import List, Optional
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.tranca import Tranca
from app.schemas.tranca import TrancaCreate, TrancaUpdate
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging_config import get_logger
from app.utils.tranca_imagens import (
    STATIC_TRANCAS,
    url_para_arquivo,
    url_imagem_principal,
    url_pertence_ao_slug,
)
from app.utils.tranca_slug import nome_para_slug

logger = get_logger("tranca_service")

MAX_FOTOS_POR_TRANCA = 6

TIPOS_IMAGEM = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
EXTENSOES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class TrancaService:
    """
    Service para categorias de trança (agrupadoras de modelos).
    """

    def __init__(self, db: Session):
        self.db = db

    def listar_trancas_ativas(self, company_id: Optional[int] = None) -> List[Tranca]:
        """
        Lista categorias ativas (catálogo público).

        Args:
            company_id: Filtrar por tenant BeautyOS.

        Returns:
            Lista de categorias ativas.
        """
        q = self.db.query(Tranca).filter(
            Tranca.ativo == True,
            Tranca.deleted_at.is_(None),
        )
        if company_id is not None:
            q = q.filter(Tranca.company_id == company_id)
        return q.all()

    def listar_todas(self, company_id: Optional[int] = None) -> List[Tranca]:
        """
        Lista todas as categorias (admin).

        Args:
            company_id: Filtrar por tenant.

        Returns:
            Lista de categorias.
        """
        q = self.db.query(Tranca).filter(Tranca.deleted_at.is_(None))
        if company_id is not None:
            q = q.filter(Tranca.company_id == company_id)
        return q.all()

    def buscar_por_id(self, tranca_id: int) -> Optional[Tranca]:
        """Busca categoria por ID."""
        return self.db.query(Tranca).filter(
            Tranca.id == tranca_id,
            Tranca.deleted_at.is_(None),
        ).first()

    def obter_tranca(self, tranca_id: int) -> Tranca:
        """Obtém categoria ou lança NotFoundError."""
        tranca = self.buscar_por_id(tranca_id)
        if not tranca:
            raise NotFoundError("Trança", str(tranca_id))
        return tranca

    def criar_tranca(self, tranca_data: TrancaCreate, company_id: Optional[int] = None) -> Tranca:
        """
        Cria nova categoria (sem preço/duração).

        Args:
            tranca_data: Dados da categoria.
            company_id: Tenant BeautyOS.

        Returns:
            Tranca criada.
        """
        logger.info(f"Criando categoria: {tranca_data.nome}")

        nome_existente = (
            self.db.query(Tranca)
            .filter(
                Tranca.nome.ilike(tranca_data.nome.strip()),
                Tranca.deleted_at.is_(None),
            )
        )
        if company_id is not None:
            nome_existente = nome_existente.filter(Tranca.company_id == company_id)
        nome_existente = nome_existente.first()
        if nome_existente:
            raise ValidationError(f"Já existe um tipo com o nome '{tranca_data.nome}'")

        payload = tranca_data.model_dump()
        tranca = Tranca(**payload, company_id=company_id)
        self.db.add(tranca)
        self.db.commit()
        self.db.refresh(tranca)

        logger.info(f"Categoria criada: ID {tranca.id} - {tranca.nome}")
        return tranca

    def atualizar_tranca(self, tranca_id: int, tranca_data: TrancaUpdate) -> Tranca:
        """
        Atualiza categoria existente (nome, descrição, capa, status).

        Args:
            tranca_id: ID da categoria.
            tranca_data: Campos a atualizar.

        Returns:
            Tranca atualizada.
        """
        tranca = self.obter_tranca(tranca_id)
        update_data = tranca_data.model_dump(exclude_unset=True)

        if "nome" in update_data:
            nome = update_data["nome"].strip()
            duplicado = (
                self.db.query(Tranca)
                .filter(
                    Tranca.nome.ilike(nome),
                    Tranca.id != tranca_id,
                    Tranca.deleted_at.is_(None),
                )
                .first()
            )
            if duplicado:
                raise ValidationError(f"Já existe um tipo com o nome '{nome}'")
            update_data["nome"] = nome

        for key, value in update_data.items():
            setattr(tranca, key, value)

        self.db.commit()
        self.db.refresh(tranca)
        return tranca

    def deletar_tranca(self, tranca_id: int) -> bool:
        """Remove categoria (soft delete)."""
        from datetime import datetime
        tranca = self.obter_tranca(tranca_id)
        tranca.deleted_at = datetime.utcnow()
        self.db.commit()
        return True

    def normalizar_imagens(self, imagens) -> List[str]:
        """Garante que imagens seja lista de URLs."""
        if imagens is None:
            return []
        if isinstance(imagens, str):
            import json
            try:
                parsed = json.loads(imagens)
                return parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                return []
        return list(imagens) if isinstance(imagens, list) else []

    def sincronizar_imagens_do_disco(
        self,
        tranca_id: int,
        base_url: str = "http://localhost:8000",
    ) -> Tranca:
        """Importa foto principal se capa estiver vazia."""
        tranca = self.obter_tranca(tranca_id)
        slug = nome_para_slug(tranca.nome)
        imagens = self.normalizar_imagens(tranca.imagens)
        imagens = [u for u in imagens if url_pertence_ao_slug(u, slug)]

        if not imagens:
            principal = url_imagem_principal(slug, base_url)
            if principal:
                imagens = [principal]

        tranca.imagens = imagens
        self.db.commit()
        self.db.refresh(tranca)
        self._sync_service_images(tranca_id)
        return tranca

    def definir_imagens(self, tranca_id: int, imagens: List[str]) -> Tranca:
        """Define imagens de capa da categoria."""
        tranca = self.obter_tranca(tranca_id)
        if len(imagens) > MAX_FOTOS_POR_TRANCA:
            raise ValidationError(
                f"Máximo de {MAX_FOTOS_POR_TRANCA} fotos de capa por categoria."
            )
        tranca.imagens = imagens
        self.db.commit()
        self.db.refresh(tranca)
        self._sync_service_images(tranca_id)
        return tranca

    async def adicionar_imagem(
        self,
        tranca_id: int,
        arquivo: UploadFile,
        base_url: str = "http://localhost:8000",
    ) -> Tranca:
        """Upload de foto de capa ou modelo (sincroniza service_images)."""
        tranca = self.obter_tranca(tranca_id)
        content_type = (arquivo.content_type or "").lower()
        if content_type not in TIPOS_IMAGEM:
            raise ValidationError("Formato inválido. Use JPG, PNG ou WEBP.")

        imagens_atuais = self.normalizar_imagens(tranca.imagens)
        if len(imagens_atuais) >= MAX_FOTOS_POR_TRANCA:
            raise ValidationError(
                f"Máximo de {MAX_FOTOS_POR_TRANCA} fotos por categoria."
            )

        conteudo = await arquivo.read()
        if len(conteudo) > 5 * 1024 * 1024:
            raise ValidationError("Imagem muito grande. Máximo: 5 MB.")
        if len(conteudo) == 0:
            raise ValidationError("Arquivo vazio.")

        STATIC_TRANCAS.mkdir(parents=True, exist_ok=True)
        slug = nome_para_slug(tranca.nome)
        proximo = len(imagens_atuais) + 1
        ext = EXTENSOES.get(content_type, ".jpg")
        nome_arquivo = f"{slug}-{proximo}{ext}" if proximo > 1 else f"{slug}{ext}"
        caminho = STATIC_TRANCAS / nome_arquivo

        if proximo == 1 and caminho.exists():
            nome_arquivo = f"{slug}-1{ext}"
            caminho = STATIC_TRANCAS / nome_arquivo

        with open(caminho, "wb") as f:
            f.write(conteudo)

        base = base_url.rstrip("/")
        nova_url = f"{base}/static/trancas/{nome_arquivo}"
        if nova_url not in imagens_atuais:
            imagens_atuais.append(nova_url)

        tranca.imagens = imagens_atuais
        self.db.commit()
        self.db.refresh(tranca)
        logger.info(f"Imagem adicionada à categoria {tranca_id}: {nome_arquivo}")
        self._sync_service_images(tranca_id)
        return tranca

    def remover_imagem(self, tranca_id: int, imagem_id: int) -> Tranca:
        """Remove modelo/foto do álbum."""
        from datetime import datetime
        from app.services.service_image_service import ServiceImageService

        tranca = self.obter_tranca(tranca_id)
        image_service = ServiceImageService(self.db)
        img = image_service.validar_imagem_da_tranca(tranca_id, imagem_id)

        imagens = self.normalizar_imagens(tranca.imagens)
        if img.url in imagens:
            imagens = [u for u in imagens if u != img.url]
        tranca.imagens = imagens

        img.deleted_at = datetime.utcnow()

        arquivo = url_para_arquivo(img.url)
        if arquivo:
            try:
                arquivo.unlink(missing_ok=True)
            except OSError as e:
                logger.warning(f"Não foi possível remover arquivo {arquivo}: {e}")

        self.db.commit()
        self.db.refresh(tranca)
        self._sync_service_images(tranca_id)
        return tranca

    def _sync_service_images(self, tranca_id: int) -> None:
        """Sincroniza modelos após alteração na galeria."""
        from app.services.service_image_service import ServiceImageService
        ServiceImageService(self.db).sincronizar_da_tranca(tranca_id)

