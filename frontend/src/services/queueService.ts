/**
 * Service da fila operacional — API /queue
 */
import api from '../config/api';

export type QueueEntryStatus =
  | 'waiting'
  | 'called'
  | 'checked_in'
  | 'in_service'
  | 'completed'
  | 'cancelled';

export interface QueueEntry {
  id: number;
  agendamento_id?: number;
  cliente_id: number;
  cliente_nome: string;
  tranca_nome?: string;
  modelo_nome?: string;
  posicao: number;
  data: string;
  horario_entrada?: string;
  status: QueueEntryStatus;
  observacoes?: string;
  mesmo_dia: boolean;
  created_at: string;
}

export interface QueueJoinRequest {
  cliente_id: number;
  tranca_id: number;
  service_image_id: number;
  observacoes?: string;
  mesmo_dia?: boolean;
}

export const queueService = {
  listar: async (data?: string) => {
    const response = await api.get<{ data: string; total: number; entries: QueueEntry[] }>(
      '/queue',
      { params: data ? { data } : {} },
    );
    return response.data;
  },

  entrar: async (dados: QueueJoinRequest): Promise<QueueEntry> => {
    const response = await api.post<QueueEntry>('/queue/join', dados);
    return response.data;
  },

  chamar: async (id: number) => api.put(`/queue/${id}/call`),
  checkin: async (id: number) => api.put(`/queue/${id}/checkin`),
  iniciar: async (id: number) => api.put(`/queue/${id}/start`),
  concluir: async (id: number) => api.put(`/queue/${id}/complete`),
};

/**
 * Pagamentos de reserva — paths booking-first (R4-F13).
 *
 * Successors de `/payments/deposit` e `/payments/final` (410 desde R4-F10).
 */
export const paymentReservationService = {
  /**
   * Confirma sinal em booking core-only.
   *
   * @param bookingId - ID ``core_bookings``.
   */
  confirmarDeposito: async (bookingId: number, _transaction_id?: string) =>
    api.post(`/admin/pagamentos/booking/${bookingId}/confirmar-sinal`),

  /**
   * Confirma pagamento final em booking core-only.
   *
   * @param bookingId - ID ``core_bookings``.
   */
  confirmarFinal: async (bookingId: number, _transaction_id?: string) =>
    api.post(`/admin/pagamentos/booking/${bookingId}/confirmar-final`),

  /**
   * Lista pagamentos sync por booking_id.
   *
   * @param bookingId - ID ``core_bookings``.
   */
  listar: async (bookingId: number) =>
    api.get('/v1/payments', { params: { booking_id: bookingId } }),
};
