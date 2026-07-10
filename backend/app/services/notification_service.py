"""
Service de Notificações
Gerencia envio de notificações automáticas
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
from app.models.notification_log import NotificationLog, NotificationType, NotificationStatus
from app.models.agendamento import Agendamento, StatusAgendamento
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
    
    def enviar_confirmacao_agendamento(self, agendamento_id: int) -> NotificationLog:
        """
        Envia notificação de confirmação de agendamento
        """
        agendamento = self.db.query(Agendamento).filter(
            Agendamento.id == agendamento_id
        ).first()
        
        if not agendamento:
            raise ValueError(f"Agendamento {agendamento_id} não encontrado")
        
        # Envia WhatsApp
        resultado = self.whatsapp.enviar_confirmacao_agendamento(
            telefone=agendamento.cliente.telefone,
            nome_cliente=agendamento.cliente.nome,
            data_hora=agendamento.data_hora,
            tipo_tranca=agendamento.tranca.nome if agendamento.tranca else "Trança"
        )
        
        # Registra log
        log = NotificationLog(
            agendamento_id=agendamento_id,
            cliente_id=agendamento.cliente_id,
            tipo=NotificationType.WHATSAPP,
            status=NotificationStatus.ENVIADA if resultado.get("status") == "enviada" else NotificationStatus.FALHA,
            destinatario=agendamento.cliente.telefone,
            mensagem=f"Confirmação de agendamento - {agendamento.tranca.nome if agendamento.tranca else 'Trança'}",
            enviada_at=datetime.now() if resultado.get("status") == "enviada" else None,
            erro=resultado.get("error") if resultado.get("status") != "enviada" else None
        )
        
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        
        return log
    
    def enviar_lembretes_pendentes(self) -> List[NotificationLog]:
        """
        Envia lembretes para agendamentos próximos
        Executar periodicamente (cron job)
        """
        logs = []
        agora = datetime.now()
        
        # Lembretes 24h antes
        data_24h = agora + timedelta(hours=24)
        agendamentos_24h = self.db.query(Agendamento).filter(
            Agendamento.status == StatusAgendamento.CONFIRMADO,
            Agendamento.data_hora >= data_24h - timedelta(hours=1),
            Agendamento.data_hora <= data_24h + timedelta(hours=1)
        ).all()
        
        for agendamento in agendamentos_24h:
            # Verifica se já foi enviado
            log_existente = self.db.query(NotificationLog).filter(
                NotificationLog.agendamento_id == agendamento.id,
                NotificationLog.tipo == NotificationType.WHATSAPP,
                NotificationLog.status == NotificationStatus.ENVIADA
            ).first()
            
            if not log_existente:
                resultado = self.whatsapp.enviar_lembrete_24h(
                    telefone=agendamento.cliente.telefone,
                    nome_cliente=agendamento.cliente.nome,
                    data_hora=agendamento.data_hora
                )
                
                log = NotificationLog(
                    agendamento_id=agendamento.id,
                    cliente_id=agendamento.cliente_id,
                    tipo=NotificationType.WHATSAPP,
                    status=NotificationStatus.ENVIADA if resultado.get("status") == "enviada" else NotificationStatus.FALHA,
                    destinatario=agendamento.cliente.telefone,
                    mensagem="Lembrete 24h antes",
                    enviada_at=datetime.now() if resultado.get("status") == "enviada" else None
                )
                self.db.add(log)
                logs.append(log)
        
        # Lembretes 3h antes
        data_3h = agora + timedelta(hours=3)
        agendamentos_3h = self.db.query(Agendamento).filter(
            Agendamento.status == StatusAgendamento.CONFIRMADO,
            Agendamento.data_hora >= data_3h - timedelta(minutes=30),
            Agendamento.data_hora <= data_3h + timedelta(minutes=30)
        ).all()
        
        for agendamento in agendamentos_3h:
            resultado = self.whatsapp.enviar_lembrete_3h(
                telefone=agendamento.cliente.telefone,
                nome_cliente=agendamento.cliente.nome,
                data_hora=agendamento.data_hora
            )
            
            log = NotificationLog(
                agendamento_id=agendamento.id,
                cliente_id=agendamento.cliente_id,
                tipo=NotificationType.WHATSAPP,
                status=NotificationStatus.ENVIADA if resultado.get("status") == "enviada" else NotificationStatus.FALHA,
                destinatario=agendamento.cliente.telefone,
                mensagem="Lembrete 3h antes",
                enviada_at=datetime.now() if resultado.get("status") == "enviada" else None
            )
            self.db.add(log)
            logs.append(log)
        
        self.db.commit()
        return logs

    def notificar_reserva_rejeitada(self, agendamento_id: int, motivo: str) -> NotificationLog:
        """Notifica cliente sobre rejeição."""
        from app.models.agendamento import Agendamento
        ag = self.db.query(Agendamento).filter(Agendamento.id == agendamento_id).first()
        msg = f"Sua reserva foi rejeitada. Motivo: {motivo}"
        return self._registrar_log(ag.cliente_id, ag.cliente.telefone, msg, agendamento_id)

    def notificar_horario_sugerido(self, agendamento_id: int) -> NotificationLog:
        """Notifica cliente sobre novo horário sugerido."""
        from app.models.agendamento import Agendamento
        ag = self.db.query(Agendamento).filter(Agendamento.id == agendamento_id).first()
        h = ag.horario_sugerido.strftime('%d/%m às %H:%M') if ag.horario_sugerido else "—"
        msg = f"Novo horário sugerido: {h}. {ag.mensagem_reagendamento or ''}"
        return self._registrar_log(ag.cliente_id, ag.cliente.telefone, msg, agendamento_id)

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
        """Notifica início do atendimento."""
        if not agendamento_id:
            return None
        from app.models.agendamento import Agendamento
        ag = self.db.query(Agendamento).filter(Agendamento.id == agendamento_id).first()
        msg = "Seu atendimento foi iniciado!"
        return self._registrar_log(ag.cliente_id, ag.cliente.telefone, msg, agendamento_id)

    def notificar_atendimento_concluido(self, agendamento_id: int) -> NotificationLog:
        """Notifica conclusão do atendimento."""
        from app.models.agendamento import Agendamento
        ag = self.db.query(Agendamento).filter(Agendamento.id == agendamento_id).first()
        msg = f"Atendimento concluído! Valor restante: R$ {ag.valor_restante}. Realize o pagamento final."
        return self._registrar_log(ag.cliente_id, ag.cliente.telefone, msg, agendamento_id)

    def notificar_pagamento_final(self, agendamento_id: int) -> NotificationLog:
        """Notifica confirmação do pagamento final."""
        from app.models.agendamento import Agendamento
        ag = self.db.query(Agendamento).filter(Agendamento.id == agendamento_id).first()
        msg = "Pagamento final confirmado. Obrigada pela preferência!"
        return self._registrar_log(ag.cliente_id, ag.cliente.telefone, msg, agendamento_id)

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

    def notificar_nova_reserva(self, agendamento_id: int) -> NotificationLog:
        """Notifica administrador sobre nova reserva criada."""
        from app.models.agendamento import Agendamento
        ag = self.db.query(Agendamento).filter(Agendamento.id == agendamento_id).first()
        if not ag:
            raise ValueError("Agendamento não encontrado")
        msg = f"Nova reserva #{ag.id} — {ag.cliente.nome} em {ag.data_hora.strftime('%d/%m %H:%M')}"
        return self._registrar_log(ag.cliente_id, "admin@sala", msg, agendamento_id)

    def notificar_reserva_aguardando_aprovacao(self, agendamento_id: int) -> NotificationLog:
        """Notifica cliente que sinal foi recebido e aguarda aprovação."""
        from app.models.agendamento import Agendamento
        ag = self.db.query(Agendamento).filter(Agendamento.id == agendamento_id).first()
        msg = (
            f"Olá {ag.cliente.nome}! Recebemos seu sinal. "
            f"Sua reserva para {ag.data_hora.strftime('%d/%m às %H:%M')} "
            f"aguarda confirmação da profissional."
        )
        return self._registrar_log(ag.cliente_id, ag.cliente.telefone, msg, agendamento_id)

    def notificar_reserva_aprovada(self, agendamento_id: int) -> NotificationLog:
        """Notifica cliente que reserva foi confirmada."""
        from app.models.agendamento import Agendamento
        ag = self.db.query(Agendamento).filter(Agendamento.id == agendamento_id).first()
        msg = (
            f"Reserva confirmada! {ag.data_hora.strftime('%d/%m às %H:%M')}. "
            f"Te esperamos no salão."
        )
        return self._registrar_log(ag.cliente_id, ag.cliente.telefone, msg, agendamento_id)

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

