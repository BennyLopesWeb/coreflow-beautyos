"""
Service de Notificações
Gerencia envio de notificações automáticas

.. deprecated:: 2.11.0-r4-f8
    A tabela ``agendamentos`` foi removida (DROP físico — ADR-024 sunset /
    RFC-003 M11+ — ver ``docs/sprints/R4-F8.md``). Todos os métodos que
    consultavam ``Agendamento`` diretamente (``enviar_confirmacao_agendamento``,
    ``enviar_lembretes_pendentes``, ``notificar_reserva_rejeitada``,
    ``notificar_horario_sugerido``, ``notificar_atendimento_iniciado``,
    ``notificar_atendimento_concluido``, ``notificar_pagamento_final``,
    ``notificar_nova_reserva``, ``notificar_reserva_aguardando_aprovacao``,
    ``notificar_reserva_aprovada``) tornaram-se no-ops (retornam ``None``/
    lista vazia, logando um aviso) — nenhum caminho de escrita ativo cria
    ``Agendamento`` desde R3-F2/R4-F3/R4-F4, então essas notificações já
    não disparavam na prática. Métodos baseados em ``QueueEntry``/``Fila``
    (``notificar_entrada_fila_operacional``, ``notificar_cliente_chamado``,
    ``notificar_nova_fila`` e afins) continuam ativos.
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
from app.models.notification_log import NotificationLog, NotificationType, NotificationStatus
from app.integrations.whatsapp import WhatsAppService
from app.core.logging_config import get_logger

logger = get_logger("notification_service")


class NotificationService:
    """
    Service para gerenciamento de notificações
    Agenda e envia notificações automáticas
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.whatsapp = WhatsAppService()
    
    def enviar_confirmacao_agendamento(self, agendamento_id: int) -> Optional[NotificationLog]:
        """
        Envia notificação de confirmação de agendamento legado.

        .. deprecated:: 2.11.0-r4-f8
            Tabela ``agendamentos`` removida — sem call-site ativo em
            produção. No-op: loga aviso e retorna ``None``.

        Args:
            agendamento_id: ID legado (ignorado).

        Returns:
            None.
        """
        logger.warning(
            "enviar_confirmacao_agendamento(%s) é no-op — tabela agendamentos "
            "removida em R4-F8", agendamento_id,
        )
        return None

    def enviar_lembretes_pendentes(self) -> List[NotificationLog]:
        """
        Envia lembretes para agendamentos próximos (24h/3h antes).

        .. deprecated:: 2.11.0-r4-f8
            A tabela ``agendamentos`` foi removida (DROP físico — ADR-024
            sunset / RFC-003 M11+). Nenhum caminho de escrita ativo cria
            ``Agendamento`` desde R3-F2/R4-F3/R4-F4, então não há mais
            lembretes legado a enviar. Equivalente core-only (via
            ``CoreBooking.scheduled_at``) fica como débito residual — ver
            ``docs/sprints/R4-F8.md``. Chamado por
            ``POST /notifications/enviar-lembretes`` (cron).

        Returns:
            Lista vazia.
        """
        return []

    def notificar_reserva_rejeitada(self, agendamento_id: int, motivo: str) -> Optional[NotificationLog]:
        """
        Notifica cliente sobre rejeição de reserva legado.

        .. deprecated:: 2.11.0-r4-f8
            Tabela ``agendamentos`` removida — sem call-site ativo (o
            único chamador, ``AgendamentoService``, sempre levanta
            ``NotFoundError`` antes de chegar aqui). No-op: loga e
            retorna ``None``.

        Args:
            agendamento_id: ID legado (ignorado).
            motivo: Ignorado.

        Returns:
            None.
        """
        logger.warning(
            "notificar_reserva_rejeitada(%s) é no-op — tabela agendamentos "
            "removida em R4-F8", agendamento_id,
        )
        return None

    def notificar_horario_sugerido(self, agendamento_id: int) -> Optional[NotificationLog]:
        """
        Notifica cliente sobre novo horário sugerido (reserva legado).

        .. deprecated:: 2.11.0-r4-f8
            Tabela ``agendamentos`` removida — sem call-site ativo. No-op:
            loga e retorna ``None``.

        Args:
            agendamento_id: ID legado (ignorado).

        Returns:
            None.
        """
        logger.warning(
            "notificar_horario_sugerido(%s) é no-op — tabela agendamentos "
            "removida em R4-F8", agendamento_id,
        )
        return None

    def notificar_entrada_fila_operacional(self, entry_id: int) -> NotificationLog:
        """Notifica admin sobre entrada na fila operacional."""
        from app.models.queue_entry import QueueEntry
        entry = self.db.query(QueueEntry).filter(QueueEntry.id == entry_id).first()
        urgente = " URGENTE" if entry.mesmo_dia else ""
        msg = f"Entrada na fila operacional{urgente}: cliente #{entry.cliente_id}"
        return self._registrar_log(entry.cliente_id, "admin@sala", msg)

    def notificar_cliente_chamado(self, entry_id: int) -> NotificationLog:
        """Notifica cliente que foi chamado."""
        from app.models.queue_entry import QueueEntry
        entry = self.db.query(QueueEntry).filter(QueueEntry.id == entry_id).first()
        cliente = entry.cliente
        msg = f"Olá {cliente.nome}! Você foi chamada — dirija-se ao atendimento."
        return self._registrar_log(entry.cliente_id, cliente.telefone, msg, entry.agendamento_id)

    def notificar_atendimento_iniciado(self, agendamento_id: Optional[int]) -> Optional[NotificationLog]:
        """
        Notifica início do atendimento (reserva legado).

        .. deprecated:: 2.11.0-r4-f8
            Tabela ``agendamentos`` removida — chamado por
            ``QueueEntryService.iniciar`` apenas no fallback legado
            (``entry.agendamento_id`` sem ``booking_id``), que nunca mais
            ocorre para entradas criadas após R4-F3. No-op: loga e
            retorna ``None``.

        Args:
            agendamento_id: ID legado, ou ``None``.

        Returns:
            None.
        """
        if not agendamento_id:
            return None
        logger.warning(
            "notificar_atendimento_iniciado(%s) é no-op — tabela agendamentos "
            "removida em R4-F8", agendamento_id,
        )
        return None

    def notificar_atendimento_concluido(self, agendamento_id: int) -> Optional[NotificationLog]:
        """
        Notifica conclusão do atendimento (reserva legado).

        .. deprecated:: 2.11.0-r4-f8
            Tabela ``agendamentos`` removida — sem call-site ativo. No-op:
            loga e retorna ``None``.

        Args:
            agendamento_id: ID legado (ignorado).

        Returns:
            None.
        """
        logger.warning(
            "notificar_atendimento_concluido(%s) é no-op — tabela agendamentos "
            "removida em R4-F8", agendamento_id,
        )
        return None

    def notificar_pagamento_final(self, agendamento_id: int) -> Optional[NotificationLog]:
        """
        Notifica confirmação do pagamento final (reserva legado).

        .. deprecated:: 2.11.0-r4-f8
            Tabela ``agendamentos`` removida — sem call-site ativo. No-op:
            loga e retorna ``None``.

        Args:
            agendamento_id: ID legado (ignorado).

        Returns:
            None.
        """
        logger.warning(
            "notificar_pagamento_final(%s) é no-op — tabela agendamentos "
            "removida em R4-F8", agendamento_id,
        )
        return None

    def _registrar_log(
        self,
        cliente_id: int,
        destinatario: str,
        mensagem: str,
        agendamento_id: Optional[int] = None,
    ) -> NotificationLog:
        """
        Registra log de notificação enviada (mock WhatsApp).

        Args:
            cliente_id: ID do cliente destinatário.
            destinatario: Telefone ou e-mail.
            mensagem: Texto enviado.
            agendamento_id: Reserva relacionada (opcional).

        Returns:
            NotificationLog persistido.
        """
        resultado = self.whatsapp.enviar_mensagem(destinatario, mensagem)
        log = NotificationLog(
            agendamento_id=agendamento_id,
            cliente_id=cliente_id,
            tipo=NotificationType.WHATSAPP,
            status=NotificationStatus.ENVIADA if resultado.get("status") == "enviada" else NotificationStatus.FALHA,
            destinatario=destinatario,
            mensagem=mensagem,
            enviada_at=datetime.now() if resultado.get("status") == "enviada" else None,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def notificar_nova_reserva(self, agendamento_id: int) -> Optional[NotificationLog]:
        """
        Notifica administrador sobre nova reserva legado criada.

        .. deprecated:: 2.11.0-r4-f8
            Tabela ``agendamentos`` removida — sem call-site ativo
            (``AgendamentoService.criar_agendamento`` levanta
            ``BusinessRuleError`` antes de chegar aqui desde R4-F4). No-op:
            loga e retorna ``None``.

        Args:
            agendamento_id: ID legado (ignorado).

        Returns:
            None.
        """
        logger.warning(
            "notificar_nova_reserva(%s) é no-op — tabela agendamentos "
            "removida em R4-F8", agendamento_id,
        )
        return None

    def notificar_reserva_aguardando_aprovacao(self, agendamento_id: int) -> Optional[NotificationLog]:
        """
        Notifica cliente que sinal foi recebido e aguarda aprovação.

        .. deprecated:: 2.11.0-r4-f8
            Tabela ``agendamentos`` removida — chamado por
            ``WorkflowEngine._action_notify_admin`` (payload de evento
            legado, envolto em try/except — falha aqui já era tolerada
            como "fallback log only"). No-op: loga e retorna ``None``.

        Args:
            agendamento_id: ID legado (ignorado).

        Returns:
            None.
        """
        logger.warning(
            "notificar_reserva_aguardando_aprovacao(%s) é no-op — tabela "
            "agendamentos removida em R4-F8", agendamento_id,
        )
        return None

    def notificar_reserva_aprovada(self, agendamento_id: int) -> Optional[NotificationLog]:
        """
        Notifica cliente que reserva legado foi confirmada.

        .. deprecated:: 2.11.0-r4-f8
            Tabela ``agendamentos`` removida — sem call-site ativo. No-op:
            loga e retorna ``None``.

        Args:
            agendamento_id: ID legado (ignorado).

        Returns:
            None.
        """
        logger.warning(
            "notificar_reserva_aprovada(%s) é no-op — tabela agendamentos "
            "removida em R4-F8", agendamento_id,
        )
        return None

    def notificar_nova_fila(self, fila_id: int) -> NotificationLog:
        """Notifica admin sobre nova entrada na fila."""
        from app.models.fila import Fila
        fila = self.db.query(Fila).filter(Fila.id == fila_id).first()
        urgente = " (URGENTE — mesmo dia)" if fila.mesmo_dia else ""
        msg = f"Nova fila de espera{urgente}: {fila.cliente.nome} para {fila.data.strftime('%d/%m')}"
        return self._registrar_log(fila.cliente_id, "admin@sala", msg)

    def notificar_fila_contatada(self, fila_id: int) -> NotificationLog:
        """Notifica cliente que profissional entrou em contato."""
        from app.models.fila import Fila
        fila = self.db.query(Fila).filter(Fila.id == fila_id).first()
        msg = f"Olá {fila.cliente.nome}! A profissional entrará em contato para combinar seu horário."
        return self._registrar_log(fila.cliente_id, fila.cliente.telefone, msg)

    def notificar_fila_aprovada(self, fila_id: int) -> NotificationLog:
        """Notifica cliente aprovado na fila com link para pagamento."""
        from app.models.fila import Fila
        fila = self.db.query(Fila).filter(Fila.id == fila_id).first()
        msg = (
            f"Boa notícia {fila.cliente.nome}! Temos horário para você. "
            f"Acesse o app para pagar o sinal e confirmar."
        )
        return self._registrar_log(fila.cliente_id, fila.cliente.telefone, msg, fila.agendamento_id)

    def notificar_fila_rejeitada(self, fila_id: int) -> NotificationLog:
        """Notifica cliente rejeitado na fila."""
        from app.models.fila import Fila
        fila = self.db.query(Fila).filter(Fila.id == fila_id).first()
        msg = f"Olá {fila.cliente.nome}, infelizmente não conseguimos encaixe para a data solicitada."
        return self._registrar_log(fila.cliente_id, fila.cliente.telefone, msg)

    def notificar_vaga_disponivel_fila(
        self,
        data_hora: datetime,
        fila_ids: List[int],
    ) -> List[NotificationLog]:
        """
        Notifica primeiros da fila sobre vaga liberada.

        Args:
            data_hora: Horário da vaga.
            fila_ids: IDs dos itens da fila sugeridos.

        Returns:
            Logs de notificação enviados.
        """
        from app.models.fila import Fila
        logs = []
        for fid in fila_ids:
            fila = self.db.query(Fila).filter(Fila.id == fid).first()
            if not fila:
                continue
            msg = (
                f"Vaga disponível {data_hora.strftime('%d/%m às %H:%M')}! "
                f"Você está na posição {fila.posicao} da fila. Aguarde contato."
            )
            logs.append(self._registrar_log(fila.cliente_id, fila.cliente.telefone, msg))
        return logs

