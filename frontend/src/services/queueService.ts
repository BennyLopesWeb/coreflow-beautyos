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

export const paymentReservationService = {
  confirmarDeposito: async (agendamento_id: number, transaction_id?: string) =>
    api.post('/payments/deposit/admin', { agendamento_id, transaction_id }),

  confirmarFinal: async (agendamento_id: number, transaction_id?: string) =>
    api.post('/payments/final', { agendamento_id, transaction_id }),

  listar: async (reservation_id: number) =>
    api.get(`/payments/reservation/${reservation_id}`),
};
