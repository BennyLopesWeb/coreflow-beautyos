/**
 * Service para gerenciar Financeiro
 */
import api from '../config/api';
import { ResumoFinanceiro, MovimentoFinanceiro } from '../types';

export const financeiroService = {
  /**
   * Busca resumo financeiro por período
   */
  buscarResumo: async (inicio: string, fim: string): Promise<ResumoFinanceiro> => {
    const response = await api.get<ResumoFinanceiro>('/financeiro/resumo', {
      params: { inicio, fim },
    });
    return response.data;
  },

  /**
   * Registra uma saída financeira
   */
  registrarSaida: async (data: {
    descricao: string;
    valor: string;
    data: string;
  }): Promise<MovimentoFinanceiro> => {
    const response = await api.post<MovimentoFinanceiro>('/financeiro/saida', data);
    return response.data;
  },
};

