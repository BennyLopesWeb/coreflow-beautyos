/**
 * Extrai mensagem e metadados de erro a partir de respostas da API ou Axios.
 */

export type ApiFieldErrors = Record<string, string>;

export interface ParsedApiError {
  /** Mensagem principal para o usuário. */
  message: string;
  /** Código de negócio quando presente (ex.: MINIMUM_DEPOSIT_NOT_MET). */
  code?: string;
  /** HTTP status, se disponível. */
  status?: number;
  /** Erros por campo (422). */
  fieldErrors: ApiFieldErrors;
  /** Mínimo de ativação em centavos (erro de depósito). */
  minimum_activation_cents?: number;
  currency?: string;
  /** Payload bruto de detail/data para diagnóstico. */
  raw?: unknown;
}

/**
 * Normaliza ``detail`` FastAPI (string, objeto ou lista de erros).
 *
 * @param detail - Conteúdo de ``response.data.detail`` ou equivalente.
 * @param fieldErrors - Acumulador de erros por campo.
 * @returns Mensagem textual principal.
 */
function normalizeDetail(
  detail: unknown,
  fieldErrors: ApiFieldErrors,
): string | undefined {
  if (typeof detail === 'string') {
    return detail;
  }
  if (Array.isArray(detail)) {
    const parts: string[] = [];
    for (const item of detail) {
      if (item && typeof item === 'object') {
        const row = item as { loc?: unknown[]; msg?: string };
        const loc = Array.isArray(row.loc)
          ? row.loc.filter((p) => p !== 'body').join('.')
          : '';
        const msg = typeof row.msg === 'string' ? row.msg : 'inválido';
        if (loc) {
          fieldErrors[loc] = msg;
        }
        parts.push(loc ? `${loc}: ${msg}` : msg);
      }
    }
    return parts.join('; ') || undefined;
  }
  if (detail && typeof detail === 'object') {
    const obj = detail as Record<string, unknown>;
    if (typeof obj.message === 'string') {
      return obj.message;
    }
    if (typeof obj.detail === 'string') {
      return obj.detail;
    }
  }
  return undefined;
}

/**
 * Faz parse estruturado de erros Axios/API.
 *
 * @param error - Erro capturado no catch.
 * @param fallback - Mensagem padrão.
 * @returns Estrutura tipada para UI.
 */
export function parseApiError(error: unknown, fallback: string): ParsedApiError {
  const fieldErrors: ApiFieldErrors = {};
  const result: ParsedApiError = { message: fallback, fieldErrors };

  if (typeof error !== 'object' || error === null || !('response' in error)) {
    if (error instanceof Error && error.message) {
      result.message = error.message;
    }
    return result;
  }

  const response = (
    error as {
      response?: { status?: number; data?: Record<string, unknown> };
    }
  ).response;
  const data = response?.data;
  result.status = response?.status;
  result.raw = data;

  if (!data) {
    return result;
  }

  if (typeof data.message === 'string') {
    result.message = data.message;
  }

  const fromDetail = normalizeDetail(data.detail, fieldErrors);
  if (fromDetail) {
    result.message = fromDetail;
  } else if (typeof data.detail === 'object' && data.detail !== null) {
    const d = data.detail as Record<string, unknown>;
    if (typeof d.message === 'string') {
      result.message = d.message;
    }
    if (typeof d.code === 'string') {
      result.code = d.code;
    }
    if (typeof d.minimum_activation_cents === 'number') {
      result.minimum_activation_cents = d.minimum_activation_cents;
    }
    if (typeof d.currency === 'string') {
      result.currency = d.currency;
    }
  }

  if (typeof data.code === 'string') {
    result.code = data.code;
  }
  if (typeof data.minimum_activation_cents === 'number') {
    result.minimum_activation_cents = data.minimum_activation_cents;
  }
  if (typeof data.currency === 'string') {
    result.currency = data.currency;
  }

  // Envelope { error, message, errors: [...] } do error_handler
  if (Array.isArray(data.errors)) {
    normalizeDetail(data.errors, fieldErrors);
  }

  result.fieldErrors = fieldErrors;
  return result;
}

/**
 * Extrai mensagem de erro legível a partir de respostas da API ou exceções Axios.
 *
 * @param error - Erro capturado no catch (geralmente AxiosError).
 * @param fallback - Mensagem padrão quando não houver detalhe da API.
 * @returns Mensagem de erro para exibir ao usuário.
 */
export function getApiErrorMessage(error: unknown, fallback: string): string {
  return parseApiError(error, fallback).message;
}

/**
 * Indica erro de mínimo de ativação não atingido.
 *
 * @param error - Erro capturado.
 * @returns True se o código for ``MINIMUM_DEPOSIT_NOT_MET``.
 */
export function isMinimumDepositNotMet(error: unknown): boolean {
  return parseApiError(error, '').code === 'MINIMUM_DEPOSIT_NOT_MET';
}

/** Ação recomendada após falha ao salvar política admin. */
export type PolicyAdminSaveAction =
  | { kind: 'conflict_reload'; message: string }
  | { kind: 'forbidden'; message: string }
  | { kind: 'validation'; message: string; fieldErrors: ApiFieldErrors }
  | { kind: 'generic'; message: string };

/**
 * Decide o fluxo UI após erro de PUT/PATCH de booking-policy.
 *
 * - 409 → recarregar GET (não sobrescrever remoto com draft local)
 * - 403 → permissão (não validação de formulário)
 * - 422 → validação por campo
 *
 * @param error - Erro Axios/API.
 * @param fallback - Mensagem padrão.
 * @returns Ação tipada para a tela.
 */
export function resolvePolicyAdminSaveError(
  error: unknown,
  fallback = 'Não foi possível salvar',
): PolicyAdminSaveAction {
  const parsed = parseApiError(error, fallback);
  if (parsed.status === 409) {
    return { kind: 'conflict_reload', message: parsed.message };
  }
  if (parsed.status === 403) {
    return { kind: 'forbidden', message: parsed.message };
  }
  if (parsed.status === 422) {
    return {
      kind: 'validation',
      message: parsed.message,
      fieldErrors: parsed.fieldErrors,
    };
  }
  return { kind: 'generic', message: parsed.message };
}

/**
 * Indica se o formulário de política deve ser renderizado.
 *
 * Em 403 (`forbidden=true`) a UI não deve expor campos editáveis.
 *
 * @param opts - Estado da tela.
 * @returns True somente quando autenticado com permissão aparente e não loading.
 */
export function shouldRenderPolicyForm(opts: {
  forbidden: boolean;
  loading: boolean;
}): boolean {
  return !opts.loading && !opts.forbidden;
}
