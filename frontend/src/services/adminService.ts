/**
 * Service para APIs administrativas do painel BeautyOS.
 */
import api from '../config/api';
import {
  AdminDashboard,
  PagamentoAdmin,
  AgendamentoAdmin,
  ClienteCrm,
  FilaResumo,
  StatusAgendamento,
} from '../types';

export const adminService = {
  /**
   * Obtém métricas agregadas do dashboard admin.
   *
   * @returns {Promise<AdminDashboard>} Resumo financeiro e operacional.
   */
  obterDashboard: async (): Promise<AdminDashboard> => {
    const response = await api.get<AdminDashboard>('/admin/dashboard');
    return response.data;
  },

  /**
   * Lista pagamentos (sinais) de todos os agendamentos.
   *
   * @returns {Promise<PagamentoAdmin[]>} Lista de pagamentos.
   */
  listarPagamentos: async (): Promise<PagamentoAdmin[]> => {
    const response = await api.get<PagamentoAdmin[]>('/admin/pagamentos');
    return response.data;
  },

  /**
   * Lista agendamentos para gestão admin.
   *
   * @param {string} [data] - Data opcional YYYY-MM-DD.
   * @returns {Promise<AgendamentoAdmin[]>} Agendamentos com detalhes.
   */
  listarAgenda: async (data?: string): Promise<AgendamentoAdmin[]> => {
    const params = data ? { data } : {};
    const response = await api.get<AgendamentoAdmin[]>('/admin/agenda', { params });
    return response.data;
  },

  /**
   * Atualiza status de um agendamento.
   *
   * @param {number} agendamentoId - ID do agendamento.
   * @param {StatusAgendamento} status - Novo status.
   * @returns {Promise<AgendamentoAdmin>} Agendamento atualizado.
   */
  atualizarStatusAgenda: async (
    agendamentoId: number,
    status: StatusAgendamento,
  ): Promise<AgendamentoAdmin> => {
    const response = await api.patch<AgendamentoAdmin>(
      `/admin/agenda/${agendamentoId}/status`,
      { status },
    );
    return response.data;
  },

  /**
   * Consulta fila detalhada do dia (admin).
   *
   * @param {string} data - Data YYYY-MM-DD.
   * @returns {Promise<FilaResumo>} Fila do dia.
   */
  consultarFila: async (data: string): Promise<FilaResumo> => {
    const response = await api.get<FilaResumo>(`/admin/fila/${data}`);
    return response.data;
  },

  /**
   * @deprecated Desde 2.9.0-r4-f6 (ADR-024 sunset). A rota legado
   * `POST /admin/pagamentos/{agendamentoId}/confirmar-sinal` foi removida
   * e agora responde sempre `410 Gone` — use `confirmarSinalBooking` para
   * bookings core-only (criados via `POST /v1/bookings` desde R3-F2/R4-F3).
   * Mantido apenas por compatibilidade de referência; chamadas a partir de
   * 2.9.0-r4-f6 sempre lançam erro HTTP 410.
   */
  confirmarSinal: async (agendamentoId: number) => {
    const response = await api.post(`/admin/pagamentos/${agendamentoId}/confirmar-sinal`);
    return response.data;
  },

  /**
   * Confirma recebimento do sinal diretamente em um booking core (R4-F4+).
   *
   * Path primário — e único desde 2.9.0-r4-f6 — para confirmação de sinal
   * pelo admin. Atualiza `CoreBooking.deposit_paid` diretamente, sem
   * depender de `Agendamento` legado.
   *
   * @param {number} bookingId - ID `core_bookings.id`.
   * @returns {Promise<{id: number; status: string; deposit_paid: boolean}>}
   *   Booking atualizado.
   */
  confirmarSinalBooking: async (bookingId: number) => {
    const response = await api.post(`/admin/pagamentos/booking/${bookingId}/confirmar-sinal`);
    return response.data;
  },

  /**
   * Aprova reserva após pagamento (pending_approval → confirmado).
   */
  aprovarReserva: async (agendamentoId: number) => {
    const response = await api.post(`/admin/agenda/${agendamentoId}/aprovar`);
    return response.data;
  },

  /**
   * Marca item da fila como contactado.
   */
  contactarFila: async (filaId: number) => {
    const response = await api.patch(`/fila/admin/${filaId}/status`, { status: 'contacted' });
    return response.data;
  },

  /**
   * Aprova item da fila e define horário.
   */
  aprovarFila: async (filaId: number, dataHora: string) => {
    const response = await api.post(`/fila/admin/${filaId}/aprovar`, { data_hora: dataHora });
    return response.data;
  },

  /**
   * Rejeita item da fila.
   */
  rejeitarFila: async (filaId: number, motivo?: string) => {
    const response = await api.post(`/fila/admin/${filaId}/rejeitar`, null, {
      params: motivo ? { motivo } : {},
    });
    return response.data;
  },

  /**
   * Lista clientes com métricas de CRM.
   *
   * @returns {Promise<ClienteCrm[]>} Clientes com status CRM.
   */
  listarCrm: async (): Promise<ClienteCrm[]> => {
    const response = await api.get<ClienteCrm[]>('/admin/crm/clientes');
    return response.data;
  },
};
