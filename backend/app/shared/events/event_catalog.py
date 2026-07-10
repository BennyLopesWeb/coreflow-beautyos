"""
EventCatalog — catálogo machine-readable de eventos CoreFlow (R1-F1).

Sincronizado com ``docs/architecture/EventCatalog.md``.
"""
from typing import Any, Dict, List


def event_catalog_entries() -> List[Dict[str, Any]]:
    """
    Retorna catálogo completo de eventos de domínio e plataforma.

    Returns:
        Lista de dicts com event_type, status, schema, publishers, consumers.
    """
    return [
        {
            "event_type": "user.registered",
            "status": "implemented",
            "schema": "identity/domain/events.py",
            "avro": None,
            "publishers": ["IdentityService"],
            "consumers": [],
        },
        {
            "event_type": "company.created",
            "status": "implemented",
            "schema": "identity/domain/events.py",
            "avro": None,
            "publishers": ["IdentityService"],
            "consumers": [],
        },
        {
            "event_type": "reservation.created",
            "status": "implemented",
            "schema": "schemas/events/reservation.created.json",
            "avro": "reservation.created.v1.avsc",
            "publishers": ["LegacyReservationService", "BookingHandlers"],
            "consumers": ["WorkflowEngine", "PushHandlers"],
        },
        {
            "event_type": "booking.created",
            "status": "implemented",
            "schema": "schemas/events/booking.created.json",
            "avro": "booking.created.v1.avsc",
            "publishers": ["CreateBookingHandler"],
            "consumers": ["WorkflowEngine", "PushHandlers"],
        },
        {
            "event_type": "booking.approved",
            "status": "implemented",
            "schema": "schemas/events/booking.approved.json",
            "avro": "booking.approved.v2.avsc",
            "publishers": ["ApproveBookingHandler"],
            "consumers": ["WorkflowEngine", "PushHandlers"],
        },
        {
            "event_type": "booking.rejected",
            "status": "implemented",
            "schema": "schemas/events/booking.rejected.json",
            "avro": "booking.rejected.v1.avsc",
            "publishers": ["RejectBookingHandler"],
            "consumers": ["WorkflowEngine"],
        },
        {
            "event_type": "booking.cancelled",
            "status": "planned",
            "schema": None,
            "avro": None,
            "publishers": ["BookingModule"],
            "consumers": ["SchedulingEngine", "Notification"],
        },
        {
            "event_type": "booking.no_show",
            "status": "planned",
            "schema": None,
            "avro": None,
            "publishers": ["SchedulingEngine"],
            "consumers": ["CRM", "Workflow"],
        },
        {
            "event_type": "payment.deposit.confirmed",
            "status": "implemented",
            "schema": "schemas/events/payment.deposit.confirmed.json",
            "avro": "payment.deposit.confirmed.v1.avsc",
            "publishers": ["PaymentHandlers"],
            "consumers": ["BookingHandlers", "WorkflowEngine"],
        },
        {
            "event_type": "payment.received",
            "status": "planned",
            "schema": None,
            "avro": None,
            "publishers": ["PaymentModule"],
            "consumers": ["OrderModule", "Workflow"],
        },
        {
            "event_type": "customer.created",
            "status": "planned",
            "schema": None,
            "avro": None,
            "publishers": ["CustomerModule"],
            "consumers": ["AIPlatform", "CRM"],
        },
        {
            "event_type": "customer.updated",
            "status": "planned",
            "schema": None,
            "avro": None,
            "publishers": ["CustomerModule"],
            "consumers": [],
        },
        {
            "event_type": "worker.created",
            "status": "planned",
            "schema": None,
            "avro": None,
            "publishers": ["SchedulingModule"],
            "consumers": [],
        },
        {
            "event_type": "resource.updated",
            "status": "planned",
            "schema": None,
            "avro": None,
            "publishers": ["SchedulingModule"],
            "consumers": ["AvailabilityService"],
        },
        {
            "event_type": "schedule.blocked",
            "status": "planned",
            "schema": None,
            "avro": None,
            "publishers": ["SchedulingModule"],
            "consumers": ["AvailabilityService"],
        },
        {
            "event_type": "inventory.updated",
            "status": "planned",
            "schema": None,
            "avro": None,
            "publishers": ["InventoryModule"],
            "consumers": [],
        },
        {
            "event_type": "order.created",
            "status": "planned",
            "schema": None,
            "avro": None,
            "publishers": ["OrderModule"],
            "consumers": ["InvoiceModule", "Workflow"],
        },
        {
            "event_type": "invoice.generated",
            "status": "planned",
            "schema": None,
            "avro": None,
            "publishers": ["InvoiceModule"],
            "consumers": ["Notification", "Finance"],
        },
        {
            "event_type": "notification.sent",
            "status": "planned",
            "schema": None,
            "avro": None,
            "publishers": ["PushModule"],
            "consumers": ["Audit"],
        },
        {
            "event_type": "workflow.started",
            "status": "partial",
            "schema": "workflow/internal",
            "avro": None,
            "publishers": ["WorkflowEngine"],
            "consumers": [],
        },
        {
            "event_type": "workflow.completed",
            "status": "partial",
            "schema": "workflow/internal",
            "avro": None,
            "publishers": ["WorkflowEngine"],
            "consumers": [],
        },
        {
            "event_type": "workflow.failed",
            "status": "partial",
            "schema": "workflow/internal",
            "avro": None,
            "publishers": ["WorkflowEngine"],
            "consumers": [],
        },
        {
            "event_type": "outbox.dispatched",
            "status": "partial",
            "schema": "shared/events/outbox.py",
            "avro": None,
            "publishers": ["OutboxService"],
            "consumers": [],
        },
        {
            "event_type": "dlq.message.recorded",
            "status": "partial",
            "schema": "shared/events/kafka_dlq.py",
            "avro": None,
            "publishers": ["KafkaDlqService"],
            "consumers": ["DlqReplayWorker"],
        },
        {
            "event_type": "ai.agent.invoked",
            "status": "planned",
            "schema": None,
            "avro": None,
            "publishers": ["AIPlatform"],
            "consumers": ["Audit"],
        },
    ]


def event_catalog_summary() -> Dict[str, Any]:
    """
    Resumo estatístico do catálogo.

    Returns:
        Dict total, by_status counts.
    """
    entries = event_catalog_entries()
    by_status: Dict[str, int] = {}
    for entry in entries:
        status = entry["status"]
        by_status[status] = by_status.get(status, 0) + 1
    return {
        "version": "1.0",
        "total": len(entries),
        "by_status": by_status,
        "entries": entries,
    }
