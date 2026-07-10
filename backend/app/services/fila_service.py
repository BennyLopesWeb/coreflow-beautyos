"""
Service de Fila de Espera
Gerencia entrada FIFO, aprovação manual e sugestão de vagas.
"""
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, date, time, timedelta
from typing import List, Optional

from app.models.fila import Fila, StatusFila, STATUS_FILA_ATIVOS
from app.models.cliente import Cliente
from app.models.tranca import Tranca
from app.models.service_image import ServiceImage
from app.schemas.fila import (
    FilaEsperaCreate,
    FilaItemDetalhado,
    FilaAprovarRequest,
    VagaSugeridaResponse,
)
from app.core.exceptions import NotFoundError, BusinessRuleError
from app.services.service_image_service import ServiceImageService


class FilaService:
    """
    Service para fila de espera virtual (FIFO por data).
    """

    def __init__(self, db: Session):
        """
        Inicializa o service.

        Args:
            db: Sessão SQLAlchemy ativa.
        """
        self.db = db

    def _proxima_posicao(self, data_fila: date) -> int:
        """
        Calcula próxima posição FIFO para a data.

        Args:
            data_fila: Data da fila.

        Returns:
            Próximo número de posição.
        """
        ultima = (
            self.db.query(Fila)
            .filter(Fila.data == data_fila, Fila.status.in_(STATUS_FILA_ATIVOS))
            .order_by(Fila.posicao.desc())
            .first()
        )
        return (ultima.posicao + 1) if ultima else 1

    def _enriquecer(self, fila: Fila) -> FilaItemDetalhado:
        """
        Converte registro Fila em item detalhado para API.

        Args:
            fila: Registro da fila.

        Returns:
            FilaItemDetalhado com nomes resolvidos.
        """
        from app.schemas.service_image import _label_modelo

        cliente = self.db.query(Cliente).filter(Cliente.id == fila.cliente_id).first()
        tranca = self.db.query(Tranca).filter(Tranca.id == fila.tranca_id).first()
        img = self.db.query(ServiceImage).filter(ServiceImage.id == fila.service_image_id).first()
        modelo_nome = _label_modelo(img) if img else "Modelo"

        return FilaItemDetalhado(
            id=fila.id,
            posicao=fila.posicao,
            cliente_id=fila.cliente_id,
            cliente_nome=cliente.nome if cliente else "Cliente",
            cliente_telefone=cliente.telefone if cliente else "",
            tranca_id=fila.tranca_id,
            tranca_nome=tranca.nome if tranca else "Trança",
            service_image_id=fila.service_image_id,
            modelo_nome=modelo_nome,
            data=fila.data,
            horario_desejado=fila.horario_desejado,
            observacoes=fila.observacoes,
            mesmo_dia=fila.mesmo_dia,
            status=fila.status,
            agendamento_id=fila.agendamento_id,
            created_at=fila.created_at,
        )

    def consultar_fila(self, data_ref: date) -> List[Fila]:
        """
        Lista itens ativos da fila ordenados por posição.

        Args:
            data_ref: Data da fila.

        Returns:
            Lista de Fila ordenada FIFO.
        """
        return (
            self.db.query(Fila)
            .filter(Fila.data == data_ref, Fila.status.in_(STATUS_FILA_ATIVOS))
            .order_by(Fila.posicao.asc())
            .all()
        )

    def consultar_fila_detalhada(self, data_ref: date) -> List[FilaItemDetalhado]:
        """
        Consulta fila com dados enriquecidos.

        Args:
            data_ref: Data da fila.

        Returns:
            Lista de FilaItemDetalhado em ordem FIFO.
        """
        filas = self.consultar_fila(data_ref)
        return [self._enriquecer(f) for f in filas]

    def entrar_na_fila(self, dados: FilaEsperaCreate) -> Fila:
        """
        Adiciona cliente à fila de espera sem horário confirmado.

        Args:
            dados: Dados da solicitação.

        Returns:
            Fila criada.

        Raises:
            NotFoundError: Cliente/trança/modelo inválidos.
            BusinessRuleError: Cliente já na fila para a data.
        """
        cliente = self.db.query(Cliente).filter(Cliente.id == dados.cliente_id).first()
        if not cliente:
            raise NotFoundError("Cliente", str(dados.cliente_id))

        tranca = self.db.query(Tranca).filter(Tranca.id == dados.tranca_id).first()
        if not tranca or not tranca.ativo:
            raise BusinessRuleError("Categoria inválida ou inativa")

        ServiceImageService(self.db).validar_imagem_da_tranca(
            dados.tranca_id, dados.service_image_id
        )

        existente = self.db.query(Fila).filter(
            Fila.cliente_id == dados.cliente_id,
            Fila.data == dados.data_desejada,
            Fila.status.in_(STATUS_FILA_ATIVOS),
        ).first()
        if existente:
            raise BusinessRuleError("Você já está na fila para esta data")

        posicao = self._proxima_posicao(dados.data_desejada)
        fila = Fila(
            cliente_id=dados.cliente_id,
            tranca_id=dados.tranca_id,
            service_image_id=dados.service_image_id,
            data=dados.data_desejada,
            horario_desejado=dados.horario_desejado,
            observacoes=dados.observacoes,
            mesmo_dia=dados.mesmo_dia,
            posicao=posicao,
            status=StatusFila.WAITING,
        )
        self.db.add(fila)
        self.db.commit()
        self.db.refresh(fila)

        from app.services.notification_service import NotificationService
        NotificationService(self.db).notificar_nova_fila(fila.id)

        return fila

    def atualizar_status(self, fila_id: int, status: StatusFila) -> Fila:
        """
        Atualiza status de um item da fila (admin).

        Args:
            fila_id: ID do item.
            status: Novo status.

        Returns:
            Fila atualizada.
        """
        fila = self.db.query(Fila).filter(Fila.id == fila_id).first()
        if not fila:
            raise NotFoundError("Fila", str(fila_id))

        fila.status = status
        self.db.commit()
        self.db.refresh(fila)

        if status == StatusFila.CONTACTED:
            from app.services.notification_service import NotificationService
            NotificationService(self.db).notificar_fila_contatada(fila.id)

        return fila

    def aprovar_fila(self, fila_id: int, body: FilaAprovarRequest) -> Fila:
        """
        Aprova item da fila, cria reserva e solicita pagamento do sinal.

        Args:
            fila_id: ID do item na fila.
            body: Horário confirmado.

        Returns:
            Fila aprovada com agendamento vinculado.
        """
        fila = self.db.query(Fila).filter(Fila.id == fila_id).first()
        if not fila:
            raise NotFoundError("Fila", str(fila_id))
        if fila.status not in STATUS_FILA_ATIVOS:
            raise BusinessRuleError("Item não está aguardando aprovação")

        from app.schemas.agendamento import AgendamentoCreate
        from app.services.agendamento_service import AgendamentoService

        agendamento = AgendamentoService(self.db).criar_agendamento(AgendamentoCreate(
            cliente_id=fila.cliente_id,
            tranca_id=fila.tranca_id,
            service_image_id=fila.service_image_id,
            data_hora=body.data_hora,
            observacoes=fila.observacoes,
        ))

        fila.status = StatusFila.APPROVED
        fila.agendamento_id = agendamento.id
        self.db.commit()
        self.db.refresh(fila)

        from app.services.notification_service import NotificationService
        NotificationService(self.db).notificar_fila_aprovada(fila.id)

        return fila

    def rejeitar_fila(self, fila_id: int, motivo: Optional[str] = None) -> Fila:
        """
        Rejeita item da fila e reorganiza posições.

        Args:
            fila_id: ID do item.
            motivo: Motivo opcional.

        Returns:
            Fila rejeitada.
        """
        fila = self.db.query(Fila).filter(Fila.id == fila_id).first()
        if not fila:
            raise NotFoundError("Fila", str(fila_id))

        data_fila = fila.data
        posicao = fila.posicao
        fila.status = StatusFila.REJECTED
        if motivo:
            fila.observacoes = (fila.observacoes or "") + f" | Rejeitado: {motivo}"

        self._reorganizar_posicoes(data_fila, posicao)
        self.db.commit()
        self.db.refresh(fila)

        from app.services.notification_service import NotificationService
        NotificationService(self.db).notificar_fila_rejeitada(fila.id)

        return fila

    def cancelar_fila(self, fila_id: int) -> Fila:
        """
        Cancela entrada na fila (cliente ou admin).

        Args:
            fila_id: ID do item.

        Returns:
            Fila cancelada.
        """
        fila = self.db.query(Fila).filter(Fila.id == fila_id).first()
        if not fila:
            raise NotFoundError("Fila", str(fila_id))
        if fila.status not in STATUS_FILA_ATIVOS:
            raise BusinessRuleError("Item não pode ser cancelado")

        data_fila = fila.data
        posicao = fila.posicao
        fila.status = StatusFila.CANCELLED
        self._reorganizar_posicoes(data_fila, posicao)
        self.db.commit()
        self.db.refresh(fila)
        return fila

    def _reorganizar_posicoes(self, data_fila: date, posicao_removida: int) -> None:
        """
        Decrementa posição dos itens após remoção/cancelamento.

        Args:
            data_fila: Data da fila.
            posicao_removida: Posição que saiu.
        """
        afetados = self.db.query(Fila).filter(
            Fila.data == data_fila,
            Fila.posicao > posicao_removida,
            Fila.status.in_(STATUS_FILA_ATIVOS),
        ).all()
        for f in afetados:
            f.posicao -= 1

    def sugerir_vaga_liberada(
        self,
        data_hora: datetime,
        duracao_minutos: int,
        limite: int = 3,
    ) -> VagaSugeridaResponse:
        """
        Identifica primeiros da fila para uma vaga recém-liberada.

        Args:
            data_hora: Início da vaga.
            duracao_minutos: Duração do slot.
            limite: Máximo de clientes sugeridos.

        Returns:
            VagaSugeridaResponse com candidatos FIFO.
        """
        data_ref = data_hora.date()
        candidatos = self.consultar_fila_detalhada(data_ref)[:limite]

        if candidatos:
            from app.services.notification_service import NotificationService
            NotificationService(self.db).notificar_vaga_disponivel_fila(
                data_hora, [c.id for c in candidatos]
            )

        return VagaSugeridaResponse(
            data_hora=data_hora,
            duracao_minutos=duracao_minutos,
            fila_sugeridos=candidatos,
        )

    def obter_posicao_cliente(self, cliente_id: int, data_ref: date) -> Optional[int]:
        """
        Retorna posição do cliente na fila do dia.

        Args:
            cliente_id: ID do cliente.
            data_ref: Data consultada.

        Returns:
            Posição ou None se não estiver na fila.
        """
        fila = self.db.query(Fila).filter(
            Fila.cliente_id == cliente_id,
            Fila.data == data_ref,
            Fila.status.in_(STATUS_FILA_ATIVOS),
        ).first()
        return fila.posicao if fila else None
