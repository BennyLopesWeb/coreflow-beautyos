/**
 * Extrai mensagem de erro legível a partir de respostas da API ou exceções Axios.
 *
 * @param {unknown} error - Erro capturado no catch (geralmente AxiosError).
 * @param {string} fallback - Mensagem padrão quando não houver detalhe da API.
 * @returns {string} Mensagem de erro para exibir ao usuário.
 */
export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = (error as { response?: { data?: Record<string, unknown> } }).response;
    const data = response?.data;

    if (typeof data?.message === 'string') {
      return data.message;
    }

    if (typeof data?.detail === 'string') {
      return data.detail;
    }
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}
