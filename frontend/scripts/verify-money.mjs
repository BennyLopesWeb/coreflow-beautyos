/**
 * Testes determinísticos de money.ts (sem Jest/Vitest).
 * Espelha a lógica de src/utils/money.ts — manter em sync.
 *
 * Executar: npm run test:money
 */
import assert from 'node:assert/strict';

function formatWholeWithThousands(whole) {
  return String(whole).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

function formatCentsToBrl(cents) {
  if (cents == null || !Number.isInteger(cents) || cents < 0) return '';
  const whole = Math.floor(cents / 100);
  const frac = cents % 100;
  const fracStr = frac < 10 ? `0${frac}` : String(frac);
  return `R$ ${formatWholeWithThousands(whole)},${fracStr}`;
}

function parseMoneyToCents(input) {
  if (typeof input === 'number') {
    if (!Number.isFinite(input) || input < 0) return null;
    return Math.round(input * 100);
  }
  let raw = String(input).trim();
  if (!raw) return null;
  raw = raw.replace(/R\$\s?/i, '').replace(/\s/g, '');
  if (raw.startsWith('-')) return null;
  if (raw.includes(',') && raw.includes('.')) {
    raw = raw.replace(/\./g, '').replace(',', '.');
  } else if (raw.includes(',')) {
    raw = raw.replace(',', '.');
  }
  if (!/^\d+(\.\d{1,2})?$/.test(raw)) return null;
  const [wholePart, fracPart = ''] = raw.split('.');
  const whole = Number.parseInt(wholePart, 10);
  const frac = Number.parseInt((fracPart + '00').slice(0, 2), 10);
  if (!Number.isFinite(whole) || whole < 0) return null;
  if (!Number.isFinite(frac) || frac < 0 || frac > 99) return null;
  return whole * 100 + frac;
}

function resolveMinimumActivationLabel(amount, cents, currency) {
  if (currency != null && currency !== '' && String(currency).toUpperCase() !== 'BRL') {
    return null;
  }
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

// parse
assert.equal(parseMoneyToCents('1234,56'), 123456);
assert.equal(parseMoneyToCents('1.234,56'), 123456);
assert.equal(parseMoneyToCents(''), null);
assert.equal(parseMoneyToCents('-10'), null);
assert.equal(parseMoneyToCents(-10), null);
assert.equal(parseMoneyToCents('0'), 0);
assert.equal(parseMoneyToCents(0), 0);

// format
assert.equal(formatCentsToBrl(123456), 'R$ 1.234,56');
assert.equal(formatCentsToBrl(10000), 'R$ 100,00');
assert.equal(formatCentsToBrl(0), 'R$ 0,00');

// apresentação: ausência → omitir (null), nunca R$ 0,00 por ausência
assert.equal(resolveMinimumActivationLabel(null, null), null);
assert.equal(resolveMinimumActivationLabel(undefined, undefined), null);
assert.notEqual(resolveMinimumActivationLabel(null, null), 'R$ 0,00');
assert.equal(resolveMinimumActivationLabel(null, 0), 'R$ 0,00'); // zero explícito do backend

// moeda não-BRL → omitir
assert.equal(resolveMinimumActivationLabel('10,00', 1000, 'USD'), null);
assert.equal(resolveMinimumActivationLabel('10,00', 1000, 'BRL'), 'R$ 10,00');
assert.equal(resolveMinimumActivationLabel(null, 10000, null), 'R$ 100,00');

console.log('test:money OK');
