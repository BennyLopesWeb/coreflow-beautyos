"""
Schemas API v1 — Catalog e Offering (metamodelo CoreFlow).
"""
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime, date, time
from decimal import Decimal


class CatalogResponse(BaseModel):
    """
    Resposta de catálogo genérico.

    Attributes:
        id: ID core_catalogs.
        company_id: Tenant.
        name: Nome.
        slug: Slug URL.
        description: Descrição.
        images: URLs de capa.
        active: Ativo no catálogo.
        legacy_tranca_id: ID legado (transição).
    """

    id: int
    company_id: int
    name: str
    slug: str
    description: Optional[str] = None
    images: List[str] = []
    active: bool
    legacy_tranca_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OfferingResponse(BaseModel):
    """
    Resposta de offering genérico.

    Attributes:
        id: ID core_offerings.
        catalog_id: Catálogo pai.
        name: Nome do modelo/serviço.
        price_total: Preço.
        deposit_pct: Percentual sinal.
        deposit_amount: Valor sinal.
        duration_minutes: Duração.
        image_url: Imagem principal.
        active: Reservável.
        legacy_service_image_id: ID legado.
    """

    id: int
    company_id: int
    catalog_id: int
    name: Optional[str] = None
    description: Optional[str] = None
    price_total: Optional[Decimal] = None
    deposit_pct: Optional[Decimal] = None
    deposit_amount: Optional[Decimal] = None
    duration_minutes: Optional[int] = None
    image_url: Optional[str] = None
    active: bool
    legacy_service_image_id: Optional[int] = None

    class Config:
        from_attributes = True


class BookingCreateRequest(BaseModel):
    """
    Command body — criar booking genérico (CQRS).

    Attributes:
        customer_id: ID do cliente.
        catalog_id: ID core_catalogs.
        offering_id: ID core_offerings.
        scheduled_at: Data/hora solicitada.
        notes: Observações opcionais.
        resource_id: ID core_resources opcional (R2-F3 / P11).
    """

    customer_id: int
    catalog_id: int
    offering_id: int
    scheduled_at: datetime
    notes: Optional[str] = None
    resource_id: Optional[int] = None


class BookingRejectRequest(BaseModel):
    """
    Body para rejeição de booking genérico.

    Attributes:
        reason: Motivo da rejeição exibido ao cliente.
    """

    reason: str = "Rejeitado pela profissional"


class BookingCancelRequest(BaseModel):
    """
    Body para cancelamento de booking genérico (R2-F2b).

    Attributes:
        reason: Motivo opcional do cancelamento.
    """

    reason: Optional[str] = None


class BookingResponse(BaseModel):
    """
    Resposta de booking genérico.

    Attributes:
        id: ID core_bookings.
        customer_id: Cliente.
        catalog_id: Catálogo.
        offering_id: Offering.
        scheduled_at: Horário solicitado.
        status: Status da reserva.
        price_total: Preço snapshot.
        legacy_agendamento_id: ID legado para APIs antigas.
    """

    id: int
    company_id: int
    customer_id: int
    catalog_id: int
    offering_id: int
    scheduled_at: datetime
    approved_at: Optional[datetime] = None
    status: str
    payment_status: str
    price_total: Decimal
    deposit_amount: Decimal
    remaining_amount: Decimal
    deposit_paid: bool
    notes: Optional[str] = None
    legacy_agendamento_id: Optional[int] = None
    catalog_name: Optional[str] = None
    offering_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LocationResponse(BaseModel):
    """
    Resposta de unidade física genérica.

    Attributes:
        id: ID core_locations.
        company_id: Tenant.
        name: Nome exibido.
        slug: Slug URL.
        address: Endereço estruturado.
        timezone: Fuso IANA.
        active: Unidade operacional.
        is_default: Local padrão do tenant.
    """

    id: int
    company_id: int
    name: str
    slug: str
    address: Dict[str, Any] = {}
    timezone: Optional[str] = None
    active: bool
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True


class WorkerResponse(BaseModel):
    """
    Resposta de profissional genérico.

    Attributes:
        id: ID core_workers.
        company_id: Tenant.
        user_id: FK users.
        display_name: Nome na agenda.
        email: E-mail.
        role: Papel RBAC.
        active: Disponível para alocação.
    """

    id: int
    company_id: int
    user_id: int
    display_name: str
    email: Optional[str] = None
    role: str
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ResourceCreateRequest(BaseModel):
    """
    Body para criar resource (R2-F3).

    Attributes:
        location_id: Unidade física.
        name: Nome do recurso.
        resource_type: Tipo (chair, court, room, generic).
        capacity: Vagas simultâneas (>= 1).
        slug: Slug opcional.
        is_default: Recurso padrão do local.
    """

    location_id: int
    name: str
    resource_type: str = "chair"
    capacity: int = 1
    slug: Optional[str] = None
    is_default: bool = False


class ResourceUpdateRequest(BaseModel):
    """
    Body para atualizar resource (R2-F3).

    Attributes:
        name: Novo nome.
        capacity: Nova capacidade.
    """

    name: Optional[str] = None
    capacity: Optional[int] = None


class ResourceResponse(BaseModel):
    """
    Resposta de recurso reservável genérico.

    Attributes:
        id: ID core_resources.
        company_id: Tenant.
        location_id: Unidade física.
        name: Nome do recurso.
        slug: Slug URL.
        resource_type: Tipo (chair, court, room, generic).
        capacity: Vagas simultâneas.
        active: Disponível para reserva.
        is_default: Recurso padrão.
    """

    id: int
    company_id: int
    location_id: int
    name: str
    slug: str
    resource_type: str
    capacity: int
    active: bool
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AvailabilitySlotResponse(BaseModel):
    """
    Slot de disponibilidade genérico.

    Attributes:
        starts_at: Início do slot.
        available: Se está livre para reserva.
        duration_minutes: Duração do offering consultado.
        catalog_id: Catálogo consultado.
        offering_id: Offering consultado.
        resource_id: Recurso alocado (default se único).
        worker_id: Profissional sugerido (default se único).
    """

    starts_at: datetime
    available: bool
    duration_minutes: Optional[int] = None
    catalog_id: int
    offering_id: int
    resource_id: Optional[int] = None
    worker_id: Optional[int] = None


class ConflictCheckRequest(BaseModel):
    """
    Body para verificação de conflito de resource.

    Attributes:
        resource_id: ID core_resources.
        starts_at: Início proposto.
        ends_at: Fim proposto.
    """

    resource_id: int
    starts_at: datetime
    ends_at: datetime


class ConflictCheckResponse(BaseModel):
    """
    Resultado de detecção de conflito.

    Attributes:
        has_conflict: Se há sobreposição acima da capacity.
        resource_id: Recurso verificado.
        capacity: Capacidade do recurso.
    """

    has_conflict: bool
    resource_id: int
    capacity: int


class CustomerResponse(BaseModel):
    """
    Resposta de customer genérico CoreFlow.

    Attributes:
        id: ID core_customers.
        company_id: Tenant.
        name: Nome.
        phone: Telefone.
        email: E-mail opcional.
        active: Ativo.
        legacy_cliente_id: ID legado clientes.
        created_at: Data de criação.
    """

    id: int
    company_id: int
    name: str
    phone: str
    email: Optional[str] = None
    active: bool
    legacy_cliente_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BookingV1Response(BaseModel):
    """
    Resposta simplificada de booking v1 para frontend.

    Attributes:
        id: ID core_bookings.
        legacy_agendamento_id: ID para APIs legado (pagamento/comprovante).
        customer_id: ID cliente.
        status: Status da reserva.
        scheduled_at: Horário.
    """

    id: int
    legacy_agendamento_id: Optional[int] = None
    customer_id: int
    status: str
    scheduled_at: datetime
    price_total: Decimal
    deposit_amount: Decimal


class PaymentResponse(BaseModel):
    """Resposta de pagamento genérico CoreFlow (metamodelo Payment)."""

    id: int
    company_id: int
    booking_id: Optional[int] = None
    payment_type: str
    amount: Decimal
    status: str
    transaction_id: Optional[str] = None
    receipt_url: Optional[str] = None
    paid_at: Optional[datetime] = None
    legacy_payment_id: Optional[int] = None
    legacy_agendamento_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class WaitlistResponse(BaseModel):
    """
    Resposta de item na fila de espera genérica CoreFlow.

    Attributes:
        id: ID core_waitlist.
        company_id: Tenant.
        customer_id: FK core_customers.
        catalog_id: FK core_catalogs.
        offering_id: FK core_offerings.
        preferred_date: Data desejada.
        preferred_time: Horário desejado opcional.
        position: Posição FIFO.
        status: Status da fila.
        booking_id: FK core_bookings quando aprovado.
        notes: Observações.
        same_day: Atendimento no mesmo dia.
        legacy_fila_id: ID legado fila.
        legacy_cliente_id: ID legado clientes.
        created_at: Data de criação.
    """

    id: int
    company_id: int
    customer_id: Optional[int] = None
    catalog_id: Optional[int] = None
    offering_id: Optional[int] = None
    preferred_date: date
    preferred_time: Optional[time] = None
    position: int
    status: str
    booking_id: Optional[int] = None
    notes: Optional[str] = None
    same_day: bool
    legacy_fila_id: Optional[int] = None
    legacy_cliente_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    """
    Resposta de pedido comercial genérico CoreFlow.

    Attributes:
        id: ID core_orders.
        company_id: Tenant.
        booking_id: FK core_bookings.
        customer_id: ID cliente legado.
        status: open | paid | cancelled | refunded.
        total_amount: Valor total.
        paid_amount: Valor pago.
        currency: Moeda.
        legacy_agendamento_id: ID legado agendamentos.
        created_at: Data de criação.
    """

    id: int
    company_id: int
    booking_id: Optional[int] = None
    customer_id: int
    status: str
    total_amount: Decimal
    paid_amount: Decimal
    currency: str
    legacy_agendamento_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InvoiceResponse(BaseModel):
    """
    Resposta de fatura/recibo genérico CoreFlow.

    Attributes:
        id: ID core_invoices.
        company_id: Tenant.
        order_id: FK core_orders.
        booking_id: FK core_bookings.
        invoice_number: Número legível.
        description: Descrição.
        amount: Valor.
        status: issued | paid | void.
        issued_at: Data emissão.
        legacy_financeiro_id: ID legado financeiro.
        legacy_agendamento_id: ID legado agendamentos.
        created_at: Data de criação.
    """

    id: int
    company_id: int
    order_id: Optional[int] = None
    booking_id: Optional[int] = None
    invoice_number: str
    description: str
    amount: Decimal
    status: str
    issued_at: datetime
    legacy_financeiro_id: Optional[int] = None
    legacy_agendamento_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class WorkflowStepResponse(BaseModel):
    """Passo de workflow para UI admin."""

    action: str
    when: str
    params: Dict[str, Any] = {}


class WorkflowDefinitionResponse(BaseModel):
    """
    Definição de workflow exposta ao editor admin (proto).

    Attributes:
        workflow_id: ID único.
        name: Nome legível.
        plugin_id: Plugin associado.
        trigger: event_type disparador.
        enabled: Estado efetivo (YAML + override DB).
        yaml_enabled: Valor original do YAML.
        steps: Passos do fluxo.
    """

    workflow_id: str
    name: str
    plugin_id: str
    trigger: str
    enabled: bool
    yaml_enabled: bool
    steps: List[WorkflowStepResponse]


class WorkflowConfigPatch(BaseModel):
    """
    Body para habilitar/desabilitar workflow via admin.

    Attributes:
        enabled: Novo estado de habilitação.
    """

    enabled: bool


class AssetResponse(BaseModel):
    """
    Resposta de ativo/insumo genérico CoreFlow.

    Attributes:
        id: ID core_assets.
        company_id: Tenant.
        name: Nome do ativo.
        sku: Código SKU.
        asset_type: Tipo (supply, equipment…).
        unit: Unidade.
        active: Ativo no catálogo.
        legacy_inventory_item_id: ID legado inventory_items.
        created_at: Data de criação.
    """

    id: int
    company_id: int
    name: str
    sku: Optional[str] = None
    asset_type: str
    unit: str
    active: bool
    legacy_inventory_item_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InventoryResponse(BaseModel):
    """
    Resposta de nível de estoque genérico CoreFlow.

    Attributes:
        id: ID core_inventory.
        company_id: Tenant.
        asset_id: FK core_assets.
        quantity_on_hand: Quantidade disponível.
        reorder_level: Nível mínimo.
        legacy_inventory_item_id: ID legado.
        created_at: Data de criação.
    """

    id: int
    company_id: int
    asset_id: int
    quantity_on_hand: Decimal
    reorder_level: Decimal
    legacy_inventory_item_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
