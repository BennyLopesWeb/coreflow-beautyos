/**
 * Service para gerenciar a Fila de Espera
 */
import api from '../config/api';
import { FilaResumo, FilaItem, FilaEsperaCreate } from '../types';

export const filaService = {
  /**
   * Consulta a fila de uma data específica.
   *
   * @param {string} data - Data no formato YYYY-MM-DD.
   * @returns {Promise<FilaResumo>} Resumo da fila com posições e detalhes.
   */
  consultar: async (data: string): Promise<FilaResumo> => {
    const response = await api.get<FilaResumo>(`/fila/${data}`);
    return response.data;
  },

  /**
   * Cliente entra na fila de espera sem horário confirmado.
   *
   * @param {FilaEsperaCreate} dados - Dados da solicitação.
   * @returns {Promise<FilaItem>} Item criado na fila.
   */
  entrar: async (dados: FilaEsperaCreate): Promise<FilaItem> => {
    const response = await api.post<FilaItem>('/fila/entrar', dados);
    return response.data;
  },

  /**
   * Consulta posição do cliente na fila do dia.
   *
   * @param {number} clienteId - ID do cliente.
   * @param {string} data - Data YYYY-MM-DD.
   * @returns {Promise<number | null>} Posição ou null.
   */
  consultarPosicao: async (clienteId: number, data: string): Promise<number | null> => {
    const response = await api.get<{ posicao: number | null }>(
      `/fila/posicao/${clienteId}/${data}`,
    );
    return response.data.posicao;
  },
};
