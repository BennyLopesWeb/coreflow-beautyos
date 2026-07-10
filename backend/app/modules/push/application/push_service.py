"""
PushNotificationService — registro de tokens e envio mock Expo Push (CF-12).
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger
from app.integrations.expo_push import ExpoPushClient
from app.models.company import Company
from app.models.notification_log import NotificationLog, NotificationStatus, NotificationType
from app.modules.push.application.deep_link_service import DeepLinkService
from app.modules.push.domain.models import CoreDeviceToken, DevicePlatform
from app.shared.events.domain_event import DomainEvent

logger = get_logger("push_service")

EVENT_TITLES: Dict[str, str] = {
    "booking.created": "Nova reserva",
    "booking.approved": "Reserva aprovada",
    "booking.rejected": "Reserva rejeitada",
    "payment.deposit.confirmed": "Sinal confirmado",
    "reservation.created": "Nova reserva aguardando",
}


class PushNotificationService:
    """
    Gerencia tokens de dispositivo e envia push a partir de eventos de domínio.

    MVP: mock local quando ``EXPO_PUSH_LIVE=false``; API Expo quando configurado.
    """

    def __init__(self, db: Session):
        """
        Args:
            db: Sessão SQLAlchemy.
        """
        self.db = db
        self.deep_links = DeepLinkService()
        self.expo = ExpoPushClient()

    def register_device(
        self,
        company_id: int,
        user_id: int,
        expo_push_token: str,
        platform: DevicePlatform = DevicePlatform.ANDROID,
    ) -> CoreDeviceToken:
        """
        Registra ou atualiza token Expo Push do usuário no tenant.

        Args:
            company_id: ID da empresa.
            user_id: ID do usuário autenticado.
            expo_push_token: Token Expo Push.
            platform: Plataforma do dispositivo.

        Returns:
            CoreDeviceToken persistido.
        """
        existing = (
            self.db.query(CoreDeviceToken)
            .filter(CoreDeviceToken.expo_push_token == expo_push_token)
            .first()
        )
        if existing:
            existing.company_id = company_id
            existing.user_id = user_id
            existing.platform = platform
            existing.active = True
            self.db.commit()
            self.db.refresh(existing)
            return existing

        token = CoreDeviceToken(
            company_id=company_id,
            user_id=user_id,
            expo_push_token=expo_push_token,
            platform=platform,
            active=True,
        )
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def list_active_tokens(self, company_id: int) -> List[CoreDeviceToken]:
        """
        Lista tokens ativos de um tenant.

        Args:
            company_id: ID da empresa.

        Returns:
            Lista de CoreDeviceToken ativos.
        """
        return (
            self.db.query(CoreDeviceToken)
            .filter(
                CoreDeviceToken.company_id == company_id,
                CoreDeviceToken.active.is_(True),
            )
            .all()
        )

    def handle_domain_event(self, event: DomainEvent) -> List[NotificationLog]:
        """
        Reage a evento outbox/event bus enviando push com deep link.

        Args:
            event: Evento de domínio publicado.

        Returns:
            Logs de notificação criados (vazio se push desabilitado).
        """
        if not settings.PUSH_NOTIFICATIONS_ENABLED:
            return []

        route_key = self.deep_links.route_for_event(event.event_type)
        if not route_key:
            return []

        company = self.db.query(Company).filter(Company.id == event.company_id).first()
        if not company:
            return []

        plugin_id = company.plugin_id or "beauty"
        link_pair = self._build_links_for_event(
            event, company.slug, plugin_id, route_key
        )
        deep_link = link_pair["deep_link"]
        universal_link = link_pair["universal_link"]
        title = EVENT_TITLES.get(event.event_type, "CoreFlow")
        body = self._body_for_event(event)

        tokens = self.list_active_tokens(event.company_id)
        if not tokens:
            logger.info(
                f"[push] Nenhum token ativo company={event.company_id} "
                f"event={event.event_type}"
            )
            return []

        logs: List[NotificationLog] = []
        for device in tokens:
            log = self._send_push(
                token=device.expo_push_token,
                title=title,
                body=body,
                data={
                    "event_type": event.event_type,
                    "deep_link": deep_link,
                    "universal_link": universal_link,
                    "company_slug": company.slug,
                    "plugin_id": plugin_id,
                    **{k: str(v) for k, v in event.payload.items()},
                },
                agendamento_id=event.payload.get("legacy_agendamento_id")
                or event.payload.get("agendamento_id"),
            )
            logs.append(log)
        return logs

    def _build_links_for_event(
        self,
        event: DomainEvent,
        company_slug: str,
        plugin_id: str,
        route_key: str,
    ) -> Dict[str, str]:
        """
        Monta par deep_link + universal_link com IDs do payload.

        Args:
            event: Evento de domínio.
            company_slug: Slug do tenant.
            plugin_id: Plugin ativo.
            route_key: Chave da rota no manifest.

        Returns:
            Dict com deep_link e universal_link.
        """
        payload = event.payload
        booking_id = (
            payload.get("legacy_agendamento_id")
            or payload.get("agendamento_id")
            or payload.get("booking_id")
            or payload.get("reservation_id")
        )
        catalog_id = payload.get("catalog_id") or payload.get("legacy_tranca_id")

        params: Dict[str, Any] = {}
        if booking_id is not None:
            params["booking_id"] = booking_id
        if catalog_id is not None:
            params["catalog_id"] = catalog_id

        try:
            return self.deep_links.build_pair(
                company_slug, plugin_id, route_key, **params
            )
        except KeyError:
            return self.deep_links.build_pair(
                company_slug, plugin_id, "bookings_list"
            )

    def _body_for_event(self, event: DomainEvent) -> str:
        """
        Gera corpo da notificação push a partir do evento.

        Args:
            event: Evento de domínio.

        Returns:
            Texto curto para o corpo da push.
        """
        booking_id = event.payload.get("booking_id") or event.payload.get("legacy_agendamento_id")
        if event.event_type == "booking.approved":
            return f"Sua reserva #{booking_id} foi aprovada."
        if event.event_type == "booking.rejected":
            reason = event.payload.get("reason") or "sem motivo informado"
            return f"Reserva #{booking_id} rejeitada: {reason}."
        if event.event_type == "payment.deposit.confirmed":
            return "Pagamento do sinal confirmado. Obrigado!"
        if event.event_type in ("booking.created", "reservation.created"):
            return f"Nova reserva #{booking_id} aguardando ação."
        return f"Evento {event.event_type}"

    def _send_push(
        self,
        token: str,
        title: str,
        body: str,
        data: Dict[str, Any],
        agendamento_id: Optional[int] = None,
    ) -> NotificationLog:
        """
        Envia push via ExpoPushClient (live ou mock) e persiste NotificationLog.

        Args:
            token: Expo push token.
            title: Título da notificação.
            body: Corpo da mensagem.
            data: Payload extra (deep_link, universal_link, event_type, etc.).
            agendamento_id: ID legado opcional para log.

        Returns:
            NotificationLog persistido.
        """
        result = self.expo.send(
            expo_push_token=token,
            title=title,
            body=body,
            data=data,
        )
        status = NotificationStatus.ENVIADA
        if result.get("status") == "falha":
            status = NotificationStatus.FALHA

        log = NotificationLog(
            agendamento_id=agendamento_id,
            tipo=NotificationType.PUSH,
            status=status,
            destinatario=token,
            mensagem=(
                f"{title}: {body} | {data.get('deep_link', '')} "
                f"| {data.get('universal_link', '')}"
            ),
            enviada_at=datetime.utcnow() if status == NotificationStatus.ENVIADA else None,
            erro=result.get("error"),
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log
