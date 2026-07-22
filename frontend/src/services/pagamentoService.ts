/**
 * Service para gerenciar Pagamentos.
 *
 * @deprecated R4-F9 — rotas `/pagamentos/sinal*` e `/pagamentos/comprovante*`
 * respondem HTTP 410 Gone. Preferir
 * `POST /admin/pagamentos/booking/{bookingId}/confirmar-sinal` (core-only).
 */
import { Platform } from 'react-native';
import api from '../config/api';
import { PixCobranca, ComprovanteUploadResponse } from '../types';
import { ComprovanteArquivo } from '../components/ComprovantePicker';

export const pagamentoService = {
  /**
   * Gera cobrança Pix para o sinal.
   *
   * @deprecated R4-F9 — endpoint retorna 410 Gone.
   * @param {number} agendamento_id - ID do agendamento (legado).
   * @returns {Promise<PixCobranca>} Dados da cobrança Pix.
   */
  gerarCobrancaPix: async (agendamento_id: number): Promise<PixCobranca> => {
    const response = await api.post<PixCobranca>('/pagamentos/sinal/gerar', {
      agendamento_id,
    });
    return response.data;
  },

  /**
   * Confirma pagamento do sinal.
   *
   * @deprecated R4-F9 — endpoint retorna 410 Gone. Use
   * `POST /admin/pagamentos/booking/{bookingId}/confirmar-sinal`.
   * @param {number} agendamento_id - ID do agendamento (legado).
   * @returns {Promise<void>} Promise resolvida após confirmação.
   */
  confirmarSinal: async (agendamento_id: number): Promise<void> => {
    await api.post('/pagamentos/sinal', { agendamento_id });
  },

  /**
   * Envia comprovante de depósito do sinal.
   *
   * @param {number} agendamentoId - ID do agendamento.
   * @param {ComprovanteArquivo} arquivo - Arquivo selecionado pelo usuário.
   * @returns {Promise<ComprovanteUploadResponse>} Resposta com URL do comprovante.
   */
  enviarComprovante: async (
    agendamentoId: number,
    arquivo: ComprovanteArquivo,
  ): Promise<ComprovanteUploadResponse> => {
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

    const response = await api.post<ComprovanteUploadResponse>(
      `/pagamentos/comprovante/${agendamentoId}`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      },
    );
    return response.data;
  },
};
