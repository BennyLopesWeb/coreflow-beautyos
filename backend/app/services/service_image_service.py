"""
Service para imagens de tranças (galeria com ID por foto).
"""
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from decimal import Decimal

from app.models.tranca import Tranca
from app.models.service_image import ServiceImage
from app.core.exceptions import NotFoundError, ValidationError
from app.services.tranca_service import TrancaService
from app.utils.tranca_slug import nome_para_slug
from app.utils.tranca_imagens import url_pertence_ao_slug
from app.utils.service_image_precos import (
    resolver_precos_imagem,
    validar_precos,
    calcular_sinal,
    PERCENTUAL_SINAL_PADRAO,
)


class ServiceImageService:
    """
    Gerencia fotos da galeria de cada trança com ID persistente.
    """

    def __init__(self, db: Session):
        """
        Inicializa o service com sessão do banco.

        Args:
            db: Sessão SQLAlchemy ativa.
        """
        self.db = db
        self.tranca_service = TrancaService(db)

    def listar_por_tranca(self, tranca_id: int, apenas_ativos: bool = False) -> List[ServiceImage]:
        """
        Lista modelos ativos de uma categoria.

        Args:
            tranca_id: ID da categoria.
            apenas_ativos: Se True, retorna só modelos com ativo=True.

        Returns:
            Lista de ServiceImage ordenada.
        """
        q = (
            self.db.query(ServiceImage)
            .filter(
                ServiceImage.service_id == tranca_id,
                ServiceImage.deleted_at.is_(None),
            )
        )
        if apenas_ativos:
            q = q.filter(ServiceImage.ativo == True)
        return q.order_by(ServiceImage.ordem.asc()).all()

    def obter_imagem(self, imagem_id: int) -> ServiceImage:
        """
        Obtém foto por ID.

        Args:
            imagem_id: ID da ServiceImage.

        Returns:
            ServiceImage encontrada.

        Raises:
            NotFoundError: Se não existir.
        """
        img = (
            self.db.query(ServiceImage)
            .filter(
                ServiceImage.id == imagem_id,
                ServiceImage.deleted_at.is_(None),
            )
            .first()
        )
        if not img:
            raise NotFoundError("Imagem", str(imagem_id))
        return img

    def validar_imagem_da_tranca(self, tranca_id: int, imagem_id: int) -> ServiceImage:
        """
        Valida que a foto pertence ao tipo de trança informado.

        Args:
            tranca_id: ID da trança.
            imagem_id: ID da foto selecionada.

        Returns:
            ServiceImage validada.

        Raises:
            ValidationError: Se a foto não pertencer à trança.
        """
        img = self.obter_imagem(imagem_id)
        if img.service_id != tranca_id:
            raise ValidationError(
                f"A foto #{imagem_id} não pertence à trança #{tranca_id}"
            )
        return img

    @staticmethod
    def resolver_precos(img: ServiceImage, tranca: Tranca) -> dict:
        """
        Retorna preços efetivos da foto (com fallback na trança).

        Args:
            img: Foto/modelo.
            tranca: Tipo de trança pai.

        Returns:
            Dict valor_total, valor_sinal, duracao_minutos.
        """
        return resolver_precos_imagem(img)

    def _normalizar_modelo(self, img: ServiceImage) -> None:
        """
        Define defaults do modelo e recalcula sinal se preço existir.

        Args:
            img: Modelo a normalizar.
        """
        if not img.nome or not str(img.nome).strip():
            img.nome = f"Modelo {img.ordem}"
        if img.percentual_sinal is None:
            img.percentual_sinal = PERCENTUAL_SINAL_PADRAO
        if img.valor_total is not None and Decimal(str(img.valor_total)) > 0:
            pct = Decimal(str(img.percentual_sinal))
            img.valor_sinal = calcular_sinal(Decimal(str(img.valor_total)), pct)

    def atualizar_imagem(
        self,
        tranca_id: int,
        imagem_id: int,
        valor_total=None,
        duracao_minutos=None,
        nome=None,
        descricao=None,
        nivel_complexidade=None,
        quantidade_trancas=None,
        quantidade_cabelo=None,
        percentual_sinal=None,
        ativo=None,
    ) -> ServiceImage:
        """
        Atualiza dados do modelo; sinal = 30% automático.

        Args:
            tranca_id: ID da trança (categoria).
            imagem_id: ID do modelo/foto.
            valor_total: Preço individual do modelo.
            duracao_minutos: Tempo estimado em minutos.
            nome: Nome do modelo.
            descricao: Descrição do modelo.
            nivel_complexidade: baixa, media ou alta.

        Returns:
            ServiceImage atualizada.

        Raises:
            ValidationError: Se valores forem inválidos.
        """
        tranca = self.tranca_service.obter_tranca(tranca_id)
        img = self.validar_imagem_da_tranca(tranca_id, imagem_id)

        if valor_total is not None:
            img.valor_total = valor_total
        if duracao_minutos is not None:
            img.duracao_minutos = duracao_minutos
        if nome is not None:
            img.nome = nome.strip() if nome else None
        if descricao is not None:
            img.descricao = descricao.strip() if descricao else None
        if nivel_complexidade is not None:
            img.nivel_complexidade = nivel_complexidade
        if quantidade_trancas is not None:
            img.quantidade_trancas = quantidade_trancas
        if quantidade_cabelo is not None:
            img.quantidade_cabelo = quantidade_cabelo.strip() if quantidade_cabelo else None
        if percentual_sinal is not None:
            img.percentual_sinal = percentual_sinal
        if ativo is not None:
            img.ativo = ativo

        self._normalizar_modelo(img)
        if img.valor_total is None:
            raise ValidationError("Informe o preço do modelo")
        try:
            validar_precos(Decimal(str(img.valor_total)))
            if img.duracao_minutos is None or int(img.duracao_minutos) <= 0:
                raise ValidationError("Informe a duração estimada do modelo")
        except ValueError as e:
            raise ValidationError(str(e))

        self.db.commit()
        self.db.refresh(img)
        return img

    def sincronizar_da_tranca(self, tranca_id: int) -> List[ServiceImage]:
        """
        Sincroniza registros ServiceImage a partir do campo imagens[] da trança.

        Args:
            tranca_id: ID da trança.

        Returns:
            Lista atualizada de ServiceImage.
        """
        tranca = self.tranca_service.obter_tranca(tranca_id)
        urls = self.tranca_service.normalizar_imagens(tranca.imagens)
        slug = nome_para_slug(tranca.nome)
        urls = [u for u in urls if url_pertence_ao_slug(u, slug)]

        if urls != self.tranca_service.normalizar_imagens(tranca.imagens):
            tranca.imagens = urls
            self.db.commit()

        existentes = (
            self.db.query(ServiceImage)
            .filter(
                ServiceImage.service_id == tranca_id,
                ServiceImage.deleted_at.is_(None),
            )
            .all()
        )
        por_url = {img.url: img for img in existentes}
        urls_ativas = set(urls)
        resultado: List[ServiceImage] = []

        for i, url in enumerate(urls):
            ordem = i + 1
            if url in por_url:
                img = por_url[url]
                img.ordem = ordem
                img.is_principal = ordem == 1
            else:
                img = ServiceImage(
                    service_id=tranca_id,
                    url=url,
                    ordem=ordem,
                    is_principal=ordem == 1,
                    percentual_sinal=PERCENTUAL_SINAL_PADRAO,
                    ativo=True,
                )
                self.db.add(img)
            self._normalizar_modelo(img)
            resultado.append(img)

        for img in existentes:
            if img.url not in urls_ativas:
                img.deleted_at = datetime.utcnow()

        self.db.commit()
        for img in resultado:
            self.db.refresh(img)
        return resultado

    def sincronizar_todas(self) -> int:
        """
        Sincroniza galerias de todas as tranças ativas.

        Returns:
            Quantidade de tranças sincronizadas.
        """
        trancas = self.tranca_service.listar_trancas_ativas()
        for tranca in trancas:
            self.sincronizar_da_tranca(tranca.id)
        return len(trancas)
