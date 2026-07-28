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
   * Upload de comprovante legado descontinuado (R4-F13).
   *
   * A rota `/pagamentos/comprovante/*` responde 410. O admin confirma o
   * sinal via `POST /admin/pagamentos/booking/{id}/confirmar-sinal`.
   *
   * @param _bookingId - ID do booking (ignorado).
   * @param _arquivo - Arquivo (ignorado).
   * @returns Nunca — sempre rejeita com mensagem clara.
   */
  enviarComprovante: async (
    _bookingId: number,
    _arquivo: ComprovanteArquivo,
  ): Promise<ComprovanteUploadResponse> => {
    throw new Error(
      'Upload de comprovante legado foi descontinuado. ' +
        'Aguarde a confirmação do sinal pelo salão (Pagamentos).',
    );
  },
};
