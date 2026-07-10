/**
 * Service de Reservas — API /reservations
 */
import api from '../config/api';
import { ReservationStatus } from '../types';

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

export const reservationService = {
  listar: async (params?: {
    status?: ReservationStatus;
    cliente_id?: number;
    data?: string;
    pendentes?: boolean;
  }): Promise<Reservation[]> => {
    const response = await api.get<Reservation[]>('/reservations', { params });
    return response.data;
  },

  obter: async (id: number): Promise<Reservation> => {
    const response = await api.get<Reservation>(`/reservations/${id}`);
    return response.data;
  },

  criar: async (data: ReservationCreate): Promise<Reservation> => {
    const response = await api.post<Reservation>('/reservations', data);
    return response.data;
  },

  aprovar: async (id: number): Promise<Reservation> => {
    const response = await api.put<Reservation>(`/reservations/${id}/approve`);
    return response.data;
  },

  rejeitar: async (id: number, motivo: string): Promise<Reservation> => {
    const response = await api.put<Reservation>(`/reservations/${id}/reject`, { motivo });
    return response.data;
  },

  reagendar: async (
    id: number,
    novo_horario: string,
    mensagem?: string,
  ): Promise<Reservation> => {
    const response = await api.put<Reservation>(`/reservations/${id}/reschedule`, {
      novo_horario,
      mensagem,
    });
    return response.data;
  },

  aceitarReagendamento: async (id: number): Promise<Reservation> => {
    const response = await api.put<Reservation>(`/reservations/${id}/accept-reschedule`, {
      aceitar: true,
    });
    return response.data;
  },

  concluir: async (id: number): Promise<Reservation> => {
    const response = await api.put<Reservation>(`/reservations/${id}/complete`);
    return response.data;
  },

  cancelar: async (id: number, motivo?: string): Promise<Reservation> => {
    const response = await api.delete<Reservation>(`/reservations/${id}`, {
      params: motivo ? { motivo } : {},
    });
    return response.data;
  },
};
