/**
 * Service do agente inteligente de automação CRM.
 */
import api from '../config/api';
import { AgentTask, AgenteExecutarResponse } from '../types';

export const agenteService = {
  /**
   * Lista tarefas do agente.
   *
   * @param {boolean} [apenasPendentes=false] - Filtrar só pendentes.
   * @returns {Promise<AgentTask[]>} Tarefas do agente.
   */
  listarTarefas: async (apenasPendentes = false): Promise<AgentTask[]> => {
    const response = await api.get<AgentTask[]>('/admin/agente/tarefas', {
      params: { apenas_pendentes: apenasPendentes },
    });
    return response.data;
  },

  /**
   * Executa ciclo completo do agente (análise + automação).
   *
   * @returns {Promise<AgenteExecutarResponse>} Resultado da execução.
   */
  executarAutomacoes: async (): Promise<AgenteExecutarResponse> => {
    const response = await api.post<AgenteExecutarResponse>('/admin/agente/executar');
    return response.data;
  },

  /**
   * Executa manualmente uma tarefa pendente.
   *
   * @param {number} taskId - ID da tarefa.
   * @returns {Promise<AgentTask>} Tarefa executada.
   */
  executarTarefa: async (taskId: number): Promise<AgentTask> => {
    const response = await api.post<AgentTask>(`/admin/agente/tarefas/${taskId}/executar`);
    return response.data;
  },
};
