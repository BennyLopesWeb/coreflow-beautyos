"""
Metamodelo CoreFlow — conceitos genéricos orientados a serviços.

Estes tipos documentam o vocabulário ubíquo da plataforma.
Entidades ORM genéricas serão introduzidas em Sprint CF-1 (Strangler Fig).

Build Once. Configure Everywhere.
"""
from enum import Enum


class CoreConcept(str, Enum):
    """
    Conceitos fundamentais do metamodelo CoreFlow.

    Cada plugin especializa terminologia via manifest.yaml;
    o core opera sempre sobre estes conceitos genéricos.
    """

    COMPANY = "company"
    USER = "user"
    WORKER = "worker"
    CUSTOMER = "customer"
    LOCATION = "location"
    RESOURCE = "resource"
    CATALOG = "catalog"
    SERVICE = "service"
    OFFERING = "offering"
    BOOKING = "booking"
    SCHEDULE_BLOCK = "schedule_block"
    WAITLIST = "waitlist"
    OPERATIONAL_QUEUE = "operational_queue"
    PAYMENT = "payment"
    ORDER = "order"
    INVOICE = "invoice"
    FINANCE_ENTRY = "finance_entry"
    ASSET = "asset"
    INVENTORY = "inventory"


# Mapeamento documentado: conceito CoreFlow → implementação legado Beauty (Sprint 0)
LEGACY_BEAUTY_MAPPINGS: dict[str, str] = {
    CoreConcept.CATALOG.value: "Tranca",
    CoreConcept.OFFERING.value: "ServiceImage",
    CoreConcept.BOOKING.value: "Agendamento",
    CoreConcept.CUSTOMER.value: "Cliente (core_customers sync)",
    CoreConcept.SCHEDULE_BLOCK.value: "Schedule",
    CoreConcept.WAITLIST.value: "Fila",
    CoreConcept.OPERATIONAL_QUEUE.value: "QueueEntry",
    CoreConcept.COMPANY.value: "Company",
    CoreConcept.USER.value: "User",
    CoreConcept.WORKER.value: "UserCompany (owner/professional)",
    CoreConcept.LOCATION.value: "implicit_single_location",
    CoreConcept.RESOURCE.value: "implicit_single_chair",
    CoreConcept.PAYMENT.value: "Payment",
    CoreConcept.ORDER.value: "Agendamento",
    CoreConcept.INVOICE.value: "Financeiro",
    CoreConcept.ASSET.value: "InventoryItem",
}
