/**
 * Service para gerenciar Clientes
 */
import api from '../config/api';
import { Cliente } from '../types';

export const clienteService = {
  /**
   * Lista todos os clientes (admin)
   */
  listar: async (): Promise<Cliente[]> => {
    const response = await api.get<Cliente[]>('/clientes');
    return response.data;
  },

  /**
   * Busca um cliente por ID
   */
  buscarPorId: async (id: number): Promise<Cliente> => {
    const response = await api.get<Cliente>(`/clientes/${id}`);
    return response.data;
  },

  /**
   * Busca um cliente por telefone
   */
  buscarPorTelefone: async (telefone: string): Promise<Cliente | null> => {
    try {
      const response = await api.get<Cliente>(
        `/clientes/por-telefone/${encodeURIComponent(telefone.trim())}`,
      );
      return response.data;
    } catch {
      return null;
    }
  },

  /**
   * Cria um novo cliente
   */
  criar: async (data: Partial<Cliente>): Promise<Cliente> => {
    const response = await api.post<Cliente>('/clientes', data);
    return response.data;
  },

  /**
   * Atualiza um cliente (admin)
   */
  atualizar: async (id: number, data: Partial<Cliente>): Promise<Cliente> => {
    const response = await api.put<Cliente>(`/clientes/${id}`, data);
    return response.data;
  },
};

