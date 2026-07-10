/**
 * Service para gerenciar Tranças
 */
import { Platform } from 'react-native';
import api from '../config/api';
import { Tranca, TrancaCreate, TrancaUpdate, TrancaImagem, TrancaImagemUpdate } from '../types';

/** Arquivo de imagem para upload de foto de trança. */
export interface TrancaImagemArquivo {
  uri: string;
  name: string;
  type: string;
  file?: File;
}

export const trancaService = {
  /**
   * Lista todas as tranças ativas (catálogo público)
   */
  listar: async (): Promise<Tranca[]> => {
    const response = await api.get<Tranca[]>('/trancas');
    return response.data;
  },

  /**
   * Lista todas as tranças (admin — inclui inativas).
   */
  listarAdmin: async (): Promise<Tranca[]> => {
    const response = await api.get<Tranca[]>('/admin/trancas');
    return response.data;
  },

  /**
   * Busca uma trança por ID
   */
  buscarPorId: async (id: number): Promise<Tranca> => {
    const response = await api.get<Tranca>(`/trancas/${id}`);
    return response.data;
  },

  /**
   * Lista fotos da galeria com ID (para reserva).
   */
  listarImagens: async (id: number): Promise<TrancaImagem[]> => {
    const response = await api.get<TrancaImagem[]>(`/trancas/${id}/imagens`);
    return response.data;
  },

  /**
   * Adiciona foto ao álbum da trança (admin).
   */
  adicionarImagem: async (
    trancaId: number,
    arquivo: TrancaImagemArquivo,
  ): Promise<TrancaImagem[]> => {
    const formData = new FormData();

    if (Platform.OS === 'web' && arquivo.file) {
      formData.append('arquivo', arquivo.file, arquivo.name);
    } else if (Platform.OS === 'web') {
      const response = await fetch(arquivo.uri);
      const blob = await response.blob();
      formData.append('arquivo', blob, arquivo.name);
    } else {
      formData.append('arquivo', {
        uri: arquivo.uri,
        name: arquivo.name,
        type: arquivo.type,
      } as unknown as Blob);
    }

    await api.post(`/trancas/${trancaId}/imagens`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return trancaService.listarImagens(trancaId);
  },

  /**
   * Remove foto do álbum da trança (admin).
   */
  removerImagem: async (
    trancaId: number,
    imagemId: number,
  ): Promise<TrancaImagem[]> => {
    const response = await api.delete<TrancaImagem[]>(
      `/trancas/${trancaId}/imagens/${imagemId}`,
    );
    return response.data;
  },

  /**
   * Atualiza preços/duração de uma foto específica (admin).
   */
  atualizarImagem: async (
    trancaId: number,
    imagemId: number,
    data: TrancaImagemUpdate,
  ): Promise<TrancaImagem> => {
    const response = await api.patch<TrancaImagem>(
      `/trancas/${trancaId}/imagens/${imagemId}`,
      data,
    );
    return response.data;
  },

  /**
   * Cria uma nova trança (admin)
   */
  criar: async (data: TrancaCreate): Promise<Tranca> => {
    const response = await api.post<Tranca>('/trancas', data);
    return response.data;
  },

  /**
   * Atualiza uma trança (admin)
   */
  atualizar: async (id: number, data: TrancaUpdate): Promise<Tranca> => {
    const response = await api.put<Tranca>(`/trancas/${id}`, data);
    return response.data;
  },

  /**
   * Remove uma trança (admin - soft delete)
   */
  remover: async (id: number): Promise<void> => {
    await api.delete(`/trancas/${id}`);
  },
};
