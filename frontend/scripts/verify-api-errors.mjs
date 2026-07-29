/**
 * Testes de mapeamento 422/409/403 (sem Jest/Vitest).
 * Espelha parseApiError / resolvePolicyAdminSaveError / shouldRenderPolicyForm.
 *
 * Executar: npm run test:api-errors
 */
import assert from 'node:assert/strict';

function normalizeDetail(detail, fieldErrors) {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const parts = [];
    for (const item of detail) {
      if (item && typeof item === 'object') {
        const loc = Array.isArray(item.loc)
          ? item.loc.filter((p) => p !== 'body').join('.')
          : '';
        const msg = typeof item.msg === 'string' ? item.msg : 'inválido';
        if (loc) fieldErrors[loc] = msg;
        parts.push(loc ? `${loc}: ${msg}` : msg);
      }
    }
    return parts.join('; ') || undefined;
  }
  if (detail && typeof detail === 'object') {
    if (typeof detail.message === 'string') return detail.message;
    if (typeof detail.detail === 'string') return detail.detail;
  }
  return undefined;
}

function parseApiError(error, fallback) {
  const fieldErrors = {};
  const result = { message: fallback, fieldErrors };
  if (typeof error !== 'object' || error === null || !('response' in error)) {
    return result;
  }
  const response = error.response;
  const data = response?.data;
  result.status = response?.status;
  if (!data) return result;
  if (typeof data.message === 'string') result.message = data.message;
  const fromDetail = normalizeDetail(data.detail, fieldErrors);
  if (fromDetail) result.message = fromDetail;
  else if (typeof data.detail === 'object' && data.detail !== null) {
    const d = data.detail;
    if (typeof d.message === 'string') result.message = d.message;
    if (typeof d.code === 'string') result.code = d.code;
  }
  if (Array.isArray(data.errors)) normalizeDetail(data.errors, fieldErrors);
  result.fieldErrors = fieldErrors;
  return result;
}

function resolvePolicyAdminSaveError(error, fallback = 'Não foi possível salvar') {
  const parsed = parseApiError(error, fallback);
  if (parsed.status === 409) return { kind: 'conflict_reload', message: parsed.message };
  if (parsed.status === 403) return { kind: 'forbidden', message: parsed.message };
  if (parsed.status === 422) {
    return {
      kind: 'validation',
      message: parsed.message,
      fieldErrors: parsed.fieldErrors,
    };
  }
  return { kind: 'generic', message: parsed.message };
}

function shouldRenderPolicyForm({ forbidden, loading }) {
  return !loading && !forbidden;
}

function axiosErr(status, data) {
  return { response: { status, data } };
}

// 422 lista FastAPI → activation.* e reason
{
  const err = axiosErr(422, {
    detail: [
      { loc: ['body', 'activation', 'percentage'], msg: 'Field required' },
      { loc: ['body', 'reason'], msg: 'Field required' },
    ],
  });
  const parsed = parseApiError(err, 'x');
  assert.equal(parsed.status, 422);
  assert.equal(parsed.fieldErrors['activation.percentage'], 'Field required');
  assert.equal(parsed.fieldErrors.reason, 'Field required');
  const action = resolvePolicyAdminSaveError(err);
  assert.equal(action.kind, 'validation');
  assert.equal(action.fieldErrors['activation.percentage'], 'Field required');
}

// 422 detail string → não quebra
{
  const err = axiosErr(422, { detail: 'Política de booking inválida' });
  const parsed = parseApiError(err, 'x');
  assert.equal(parsed.message, 'Política de booking inválida');
  assert.equal(resolvePolicyAdminSaveError(err).kind, 'validation');
}

// 422 detail objeto → não quebra
{
  const err = axiosErr(422, { detail: { message: 'cap_cents ausente' } });
  const parsed = parseApiError(err, 'x');
  assert.equal(parsed.message, 'cap_cents ausente');
}

// 409 → conflict_reload (UI deve GET de novo; não tratar como validação)
{
  const err = axiosErr(409, { detail: 'Versão da política desatualizada' });
  const action = resolvePolicyAdminSaveError(err);
  assert.equal(action.kind, 'conflict_reload');
  assert.notEqual(action.kind, 'validation');
}

// 403 → forbidden (não validação de formulário)
{
  const err = axiosErr(403, { detail: 'Acesso restrito a administradores da empresa' });
  const action = resolvePolicyAdminSaveError(err);
  assert.equal(action.kind, 'forbidden');
  assert.notEqual(action.kind, 'validation');
  assert.equal(shouldRenderPolicyForm({ forbidden: true, loading: false }), false);
  assert.equal(shouldRenderPolicyForm({ forbidden: false, loading: false }), true);
}

console.log('test:api-errors OK');
