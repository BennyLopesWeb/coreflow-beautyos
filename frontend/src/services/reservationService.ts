/**
 * Service de Reservas — leitura/escrita via CoreFlow ``/v1/bookings`` (M-01).
 *
 * A listagem administrativa não usa mais ``GET /reservations`` (HTTP 410).
 * Campos ausentes no Core (``cliente_nome``, ``comprovante_url``) são
 * compostos via ``GET /admin/pagamentos`` (mesmo join usado pelo legado).
 */
import api from '../config/api';
import { PagamentoAdmin, ReservationStatus } from '../types';
import { clienteService } from './clienteService';

export interface Reservation {
  id: number;
  cliente_id: number;
  tranca_id: number;
  service_image_id: number;
  data_hora: string;
  horario_aprovado?: string;
  valor_total: string;
  percentual_sinal: string;
  valor_sinal: string;
  valor_restante: string;
  sinal_pago: boolean;
  status: ReservationStatus;
  status_pagamento: string;
  observacoes?: string;
  motivo_rejeicao?: string;
  horario_sugerido?: string;
  mensagem_reagendamento?: string;
  comprovante_url?: string;
  cliente_nome?: string;
  tranca_nome?: string;
  modelo_nome?: string;
  created_at: string;
}

export interface ReservationCreate {
  cliente_id: number;
  tranca_id: number;
  service_image_id: number;
  data_hora: string;
  observacoes?: string;
}

/**
 * Metadados da última chamada a ``listar`` (truncamento do teto Core).
 *
 * Mantido fora do retorno de ``listar`` para preservar
 * ``Promise<Reservation[]>`` na assinatura pública.
 */
export interface ReservationListMeta {
  /**
   * True quando a API Core devolveu pelo menos ``BOOKING_LIST_FETCH_LIMIT``
   * itens — pode haver mais registros (ou exatamente 100).
   */
  truncated: boolean;
  /** Quantidade bruta retornada por ``GET /v1/bookings`` (antes dos filtros client). */
  fetchedCount: number;
}

/** Teto hardcoded em ``BookingQueryService.list_bookings`` (backend). */
export const BOOKING_LIST_FETCH_LIMIT = 100;

/**
 * Metadados da listagem mais recente (lido pela UI após ``await listar``).
 */
export let lastReservationListMeta: ReservationListMeta = {
  truncated: false,
  fetchedCount: 0,
};

/**
 * Calcula ``percentual_sinal`` (fração 0–1) a partir de total e sinal.
 *
 * ``BookingResponse`` não expõe ``deposit_pct``; a fração é derivada.
 *
 * Args:
 *   priceTotal: Valor total do booking.
 *   depositAmount: Valor do sinal.
 *
 * Returns:
 *   String decimal (ex.: ``"0.3"``) ou ``""`` se não for calculável.
 */
function derivePercentualSinal(
  priceTotal: string | number,
  depositAmount: string | number,
): string {
  const total = Number(priceTotal);
  const deposit = Number(depositAmount);
  if (!Number.isFinite(total) || total <= 0 || !Number.isFinite(deposit) || deposit < 0) {
    return '';
  }
  return String(deposit / total);
}

/**
 * Payload de ``BookingResponse`` retornado por ``GET /v1/bookings``.
 */
interface BookingListItem {
  id: number;
  company_id: number;
  customer_id: number;
  catalog_id: number;
  offering_id: number;
  scheduled_at: string;
  approved_at?: string | null;
  status: string;
  payment_status: string;
  price_total: string | number;
  deposit_amount: string | number;
  remaining_amount: string | number;
  deposit_paid: boolean;
  notes?: string | null;
  legacy_agendamento_id?: number | null;
  catalog_name?: string | null;
  offering_name?: string | null;
  created_at: string;
}

/** Status considerados “pendentes” pela UI admin (reservas.tsx / operacional). */
const STATUS_PENDENTES = new Set([
  'pending_payment',
  'pending_approval',
  'waiting_time_confirmation',
  'pendente',
]);

/**
 * Converte um booking CoreFlow v1 para o formato ``Reservation`` da UI.
 *
 * Args:
 *   booking: Item de ``GET /v1/bookings``.
 *
 * Returns:
 *   Objeto compatível com as telas admin existentes (ainda sem nome/comprovante).
 */
function mapBookingToReservation(booking: BookingListItem): Reservation {
  return {
    id: booking.id,
    cliente_id: booking.customer_id,
    tranca_id: booking.catalog_id,
    service_image_id: booking.offering_id,
    data_hora: booking.scheduled_at,
    horario_aprovado: booking.approved_at ?? undefined,
    valor_total: String(booking.price_total),
    percentual_sinal: derivePercentualSinal(booking.price_total, booking.deposit_amount),
    valor_sinal: String(booking.deposit_amount),
    valor_restante: String(booking.remaining_amount),
    sinal_pago: booking.deposit_paid,
    status: booking.status as ReservationStatus,
    status_pagamento: booking.payment_status,
    observacoes: booking.notes ?? undefined,
    tranca_nome: booking.catalog_name ?? undefined,
    modelo_nome: booking.offering_name ?? undefined,
    created_at: booking.created_at,
  };
}

/**
 * Indica se a data do booking (ISO) corresponde ao dia ``YYYY-MM-DD``.
 *
 * Args:
 *   scheduledAt: Datetime ISO do booking.
 *   day: Dia no formato ``YYYY-MM-DD``.
 *
 * Returns:
 *   True se o prefixo de data coincidir.
 */
function matchesDay(scheduledAt: string, day: string): boolean {
  if (!day) {
    return true;
  }
  return scheduledAt.slice(0, 10) === day;
}

/**
 * Monta mapa booking_id → enriquecimento a partir de ``GET /admin/pagamentos``.
 *
 * Args:
 *   pagamentos: Itens admin (``agendamento_id`` = ``core_bookings.id``).
 *
 * Returns:
 *   Map com ``cliente_nome`` e ``comprovante_url`` por booking.
 */
function buildPagamentoEnrichmentMap(
  pagamentos: PagamentoAdmin[],
): Map<number, { cliente_nome?: string; comprovante_url?: string }> {
  const map = new Map<number, { cliente_nome?: string; comprovante_url?: string }>();
  for (const p of pagamentos) {
    map.set(p.agendamento_id, {
      cliente_nome: p.cliente_nome || undefined,
      comprovante_url: p.comprovante_url || undefined,
    });
  }
  return map;
}

/**
 * Busca nomes de clientes via ``GET /clientes`` (fallback se pagamentos falhar).
 *
 * Args:
 *   None.
 *
 * Returns:
 *   Map ``cliente.id`` → ``nome``.
 */
async function fetchClienteNomeMap(): Promise<Map<number, string>> {
  try {
    const clientes = await clienteService.listar();
    return new Map(clientes.map((c) => [c.id, c.nome]));
  } catch {
    return new Map();
  }
}

/**
 * Aplica ``cliente_nome`` e ``comprovante_url`` nas reservas mapeadas.
 *
 * Prefere dados de ``/admin/pagamentos``; completa nomes faltantes com ``/clientes``.
 *
 * Args:
 *   rows: Reservas já mapeadas do Core.
 *   pagamentoMap: Enrichment de pagamentos admin (pode estar vazio).
 *   clienteNomeMap: Fallback de nomes por ``cliente_id``.
 *
 * Returns:
 *   Nova lista com campos compostos preenchidos quando disponíveis.
 */
function enrichReservations(
  rows: Reservation[],
  pagamentoMap: Map<number, { cliente_nome?: string; comprovante_url?: string }>,
  clienteNomeMap: Map<number, string>,
): Reservation[] {
  return rows.map((row) => {
    const fromPagamento = pagamentoMap.get(row.id);
    const cliente_nome =
      fromPagamento?.cliente_nome ?? clienteNomeMap.get(row.cliente_id) ?? row.cliente_nome;
    const comprovante_url = fromPagamento?.comprovante_url ?? row.comprovante_url;
    if (cliente_nome === row.cliente_nome && comprovante_url === row.comprovante_url) {
      return row;
    }
    return { ...row, cliente_nome, comprovante_url };
  });
}

export const reservationService = {
  /**
   * Lista reservas do tenant via ``GET /v1/bookings`` (admin).
   *
   * Enriquecimento (1 chamada complementar, sem N+1):
   * - ``GET /admin/pagamentos`` → ``cliente_nome`` + ``comprovante_url``
   *   (``agendamento_id`` = booking id);
   * - fallback de nomes via ``GET /clientes`` se a chamada admin falhar
   *   ou algum booking não aparecer no join.
   *
   * Filtros ``pendentes``, ``status`` e ``data`` são aplicados no cliente
   * porque a API Core só aceita ``customer_id`` no query string.
   *
   * Args:
   *   params.status: Filtra por status exato (após map).
   *   params.cliente_id: Encaminhado como ``customer_id``.
   *   params.data: Dia ``YYYY-MM-DD`` sobre ``scheduled_at``.
   *   params.pendentes: Mantém apenas status de ação admin.
   *
   * Returns:
   *   Lista ``Reservation[]`` enriquecida. Metadados de truncamento ficam em
   *   ``lastReservationListMeta`` (preserva a assinatura pública array).
   */
  listar: async (params?: {
    status?: ReservationStatus;
    cliente_id?: number;
    data?: string;
    pendentes?: boolean;
  }): Promise<Reservation[]> => {
    const query: { customer_id?: number } = {};
    if (params?.cliente_id != null) {
      query.customer_id = params.cliente_id;
    }

    const [bookingsSettled, pagamentosSettled] = await Promise.allSettled([
      api.get<BookingListItem[]>('/v1/bookings', { params: query }),
      api.get<PagamentoAdmin[]>('/admin/pagamentos'),
    ]);

    if (bookingsSettled.status === 'rejected') {
      lastReservationListMeta = { truncated: false, fetchedCount: 0 };
      throw bookingsSettled.reason;
    }

    const fetched = bookingsSettled.value.data;
    const fetchedCount = fetched.length;
    lastReservationListMeta = {
      truncated: fetchedCount >= BOOKING_LIST_FETCH_LIMIT,
      fetchedCount,
    };

    let rows = fetched.map(mapBookingToReservation);

    const pagamentoMap =
      pagamentosSettled.status === 'fulfilled'
        ? buildPagamentoEnrichmentMap(pagamentosSettled.value.data)
        : new Map();

    const needsClienteFallback =
      pagamentosSettled.status === 'rejected' ||
      rows.some((r) => !pagamentoMap.get(r.id)?.cliente_nome);

    const clienteNomeMap = needsClienteFallback
      ? await fetchClienteNomeMap()
      : new Map<number, string>();

    rows = enrichReservations(rows, pagamentoMap, clienteNomeMap);

    if (params?.pendentes) {
      rows = rows.filter((r) => STATUS_PENDENTES.has(r.status));
    }
    if (params?.status) {
      rows = rows.filter((r) => r.status === params.status);
    }
    if (params?.data) {
      rows = rows.filter((r) => matchesDay(r.data_hora, params.data!));
    }

    return rows;
  },

  obter: async (id: number): Promise<Reservation> => {
    const response = await api.get<Reservation>(`/v1/bookings/${id}`);
    return response.data;
  },

  criar: async (data: ReservationCreate): Promise<Reservation> => {
    const response = await api.post<Reservation>('/v1/bookings', data);
    return response.data;
  },

  aprovar: async (id: number): Promise<Reservation> => {
    const response = await api.post<Reservation>(`/v1/bookings/${id}/approve`);
    return response.data;
  },

  rejeitar: async (id: number, motivo: string): Promise<Reservation> => {
    const response = await api.post<Reservation>(`/v1/bookings/${id}/reject`, {
      reason: motivo,
    });
    return response.data;
  },

  /**
   * Reagenda booking core-only (R4-F11 / ADR-026).
   *
   * Fecha o booking atual como `rescheduled` e cria um substituto.
   * Successor de `PUT /reservations/{id}/reschedule` (410 Gone).
   *
   * @param id - ID `core_bookings`.
   * @param novo_horario - Novo horário ISO.
   * @param mensagem - Motivo/mensagem opcional.
   * @returns Booking novo (substituto).
   */
  reagendar: async (
    id: number,
    novo_horario: string,
    mensagem?: string,
  ): Promise<Reservation> => {
    const response = await api.post<{
      previous_booking_id: number;
      previous_status: string;
      booking: Reservation;
    }>(`/v1/bookings/${id}/reschedule`, {
      scheduled_at: novo_horario,
      notes: mensagem,
    });
    return response.data.booking;
  },

  /**
   * @deprecated R4-F11 — fluxo two-step legado removido; `reagendar` já cria o substituto.
   * Fora do escopo M-01 (ainda 410) — ver M-02.
   */
  aceitarReagendamento: async (id: number): Promise<Reservation> => {
    const response = await api.put<Reservation>(`/reservations/${id}/accept-reschedule`, {
      aceitar: true,
    });
    return response.data;
  },

  concluir: async (id: number): Promise<Reservation> => {
    const response = await api.post<Reservation>(`/v1/bookings/${id}/complete`, {});
    return response.data;
  },

  cancelar: async (id: number, motivo?: string): Promise<Reservation> => {
    const response = await api.post<Reservation>(`/v1/bookings/${id}/cancel`, {
      reason: motivo,
    });
    return response.data;
  },

  /**
   * Marca no-show (R4-F13 / ADR-026).
   *
   * @param id - ID core_bookings.
   * @param motivo - Motivo opcional.
   */
  marcarNoShow: async (id: number, motivo?: string): Promise<Reservation> => {
    const response = await api.post<Reservation>(`/v1/bookings/${id}/no-show`, {
      reason: motivo,
    });
    return response.data;
  },
};
