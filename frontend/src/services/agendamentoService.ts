/**
 * Service para gerenciar Agendamentos
 */
import api from '../config/api';
import { coreflowService } from './coreflowService';
import { Agendamento, AgendamentoCreate, DisponibilidadeResponse, HorarioDisponivel } from '../types';

export const agendamentoService = {
  /**
   * Consulta horários disponíveis para uma data e trança.
   * Prefere CoreFlow v1 (`/v1/scheduling/availability`) com fallback legado.
   */
  consultarDisponibilidade: async (
    data: string,
    tranca_id: number,
    service_image_id?: number,
  ): Promise<HorarioDisponivel[]> => {
    if (coreflowService.useCoreflowV1()) {
      try {
        return await coreflowService.consultarDisponibilidadeV1(
          data,
          tranca_id,
          service_image_id,
        );
      } catch (error) {
        console.warn('[CoreFlow v1] fallback para /agenda/disponibilidade', error);
      }
    }

    const response = await api.get<DisponibilidadeResponse>('/agenda/disponibilidade', {
      params: {
        data: `${data}T08:00:00`,
        tranca_id,
        ...(service_image_id != null ? { service_image_id } : {}),
      },
    });
    return response.data.horarios.map((h) => ({
      horario: formatHorario(h.horario),
      disponivel: h.disponivel,
    }));
  },

  /**
   * Lista todos os agendamentos (admin)
   */
  listar: async (): Promise<Agendamento[]> => {
    const response = await api.get<Agendamento[]>('/agenda/agendamentos');
    return response.data;
  },

  /**
   * Busca um agendamento por ID
   */
  buscarPorId: async (id: number): Promise<Agendamento> => {
    const response = await api.get<Agendamento>(`/agenda/agendamentos/${id}`);
    return response.data;
  },

  /**
   * Cria um novo agendamento.
   * Prefere CoreFlow v1 (`POST /v1/bookings`) com fallback legado.
   */
  criar: async (data: AgendamentoCreate): Promise<Agendamento> => {
    if (coreflowService.useCoreflowV1()) {
      try {
        return await coreflowService.criarBookingV1(data);
      } catch (error) {
        console.warn('[CoreFlow v1] fallback para POST /agenda/agendamentos', error);
      }
    }

    const response = await api.post<Agendamento>('/agenda/agendamentos', data);
    return response.data;
  },

  /**
   * Atualiza um agendamento (admin)
   */
  atualizar: async (id: number, data: Partial<Agendamento>): Promise<Agendamento> => {
    const response = await api.put<Agendamento>(`/agenda/agendamentos/${id}`, data);
    return response.data;
  },

  /**
   * Remove um agendamento (admin - soft delete)
   */
  remover: async (id: number): Promise<void> => {
    await api.delete(`/agenda/agendamentos/${id}`);
  },
};

/**
 * Formata horário ISO ou datetime para HH:MM.
 *
 * @param {string} horario - Horário retornado pela API.
 * @returns {string} Horário no formato HH:MM.
 */
function formatHorario(horario: string): string {
  const date = new Date(horario);
  if (Number.isNaN(date.getTime())) {
    return horario.slice(11, 16);
  }
  return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

