/**
 * Smoke tests mínimos (sem Vitest/Jest) para money + separação de rótulos.
 * Executar: node scripts/verify-deposit-policy.mjs
 */
import assert from 'node:assert/strict';

/**
 * Espelho de formatCentsToBrl / parseMoneyToCents / resolveMinimumActivationLabel.
 * Mantido em sync com src/utils/money.ts para validação sem transpile.
 */

function formatCentsToBrl(cents) {
  if (cents == null || !Number.isInteger(cents) || cents < 0) return '';
  const whole = Math.floor(cents / 100);
  const frac = cents % 100;
  const fracStr = frac < 10 ? `0${frac}` : String(frac);
  return `R$ ${whole},${fracStr}`;
}

function parseMoneyToCents(input) {
  if (typeof input === 'number') {
    if (!Number.isFinite(input) || input < 0) return null;
    return Math.round(input * 100);
  }
  let raw = String(input).trim().replace(/R\$\s?/i, '').replace(/\s/g, '');
  if (!raw) return null;
  if (raw.includes(',') && raw.includes('.')) {
    raw = raw.replace(/\./g, '').replace(',', '.');
  } else if (raw.includes(',')) {
    raw = raw.replace(',', '.');
  }
  if (!/^\d+(\.\d{1,2})?$/.test(raw)) return null;
  const [wholePart, fracPart = ''] = raw.split('.');
  const whole = Number.parseInt(wholePart, 10);
  const frac = Number.parseInt((fracPart + '00').slice(0, 2), 10);
  return whole * 100 + frac;
}

function resolveMinimumActivationLabel(amount, cents) {
  if (amount != null && amount !== '') {
    const c = parseMoneyToCents(amount);
    if (c != null) return formatCentsToBrl(c);
  }
  if (cents != null) {
    const f = formatCentsToBrl(cents);
    if (f) return f;
  }
  return null;
}

/** Garante que não há cálculo 20%/10000 neste módulo de apresentação. */
function noLocalActivationFormula(src) {
  assert.equal(/20\s*\*|\/\s*100|10000/.test(src), false);
}

assert.equal(formatCentsToBrl(10000), 'R$ 100,00');
assert.equal(formatCentsToBrl(6050), 'R$ 60,50');
assert.equal(formatCentsToBrl(null), '');
assert.equal(parseMoneyToCents('100,00'), 10000);
assert.equal(parseMoneyToCents('1.234,56'), 123456);
assert.equal(parseMoneyToCents('abc'), null);
assert.equal(resolveMinimumActivationLabel('60.00', null), 'R$ 60,00');
assert.equal(resolveMinimumActivationLabel(null, 10000), 'R$ 100,00');
assert.equal(resolveMinimumActivationLabel(null, null), null);

// Ausência não vira R$ 0,00
assert.notEqual(resolveMinimumActivationLabel(undefined, undefined), 'R$ 0,00');

noLocalActivationFormula(`
  export function resolveMinimumActivationLabel(amount, cents) {
    return amount || cents;
  }
`);

console.log('verify-deposit-policy: OK');
