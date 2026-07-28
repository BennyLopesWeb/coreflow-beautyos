/**
 * Service para gerenciar Pagamentos.
 *
 * Rotas legado `/pagamentos/sinal*` e `/pagamentos/comprovante*` respondem
 * HTTP 410 Gone (R4-F9/R4-F14). Upload de comprovante core: R4-F15
 * `POST /v1/bookings/{bookingId}/comprovante`. Confirmação do sinal:
 * `POST /admin/pagamentos/booking/{bookingId}/confirmar-sinal`.
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
   * Envia comprovante de depósito vinculado a um booking core (R4-F15).
   *
   * @param {number} bookingId - ID ``core_bookings.id`` retornado por
   *   ``agendamentoService.criar`` / ``POST /v1/bookings``.
   * @param {ComprovanteArquivo} arquivo - Arquivo selecionado no picker.
   * @returns {Promise<ComprovanteUploadResponse>} URL e mensagem de confirmação.
   */
  enviarComprovante: async (
    bookingId: number,
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
      `/v1/bookings/${bookingId}/comprovante`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      },
    );
    return response.data;
  },
};
