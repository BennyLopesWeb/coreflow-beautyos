/**
 * Utilitário monetário seguro (BRL / centavos) para política de entrada.
 *
 * Não usa parseFloat/toFixed no caminho de persistência administrativa.
 */

/**
 * Formata a parte inteira com separador de milhar brasileiro.
 *
 * @param whole - Parte inteira (>= 0).
 * @returns Ex.: ``1.234``.
 */
function formatWholeWithThousands(whole: number): string {
  const digits = String(whole);
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

/**
 * Formata centavos inteiros para exibição BRL.
 *
 * @param cents - Valor em centavos (>= 0).
 * @returns Texto ``R$ 1.234,56`` ou string vazia se inválido.
 */
export function formatCentsToBrl(cents: number | null | undefined): string {
  if (cents == null || !Number.isInteger(cents) || cents < 0) {
    return '';
  }
  const whole = Math.floor(cents / 100);
  const frac = cents % 100;
  const fracStr = frac < 10 ? `0${frac}` : String(frac);
  return `R$ ${formatWholeWithThousands(whole)},${fracStr}`;
}

/**
 * Formata valor em reais (string/number) já decimal para BRL.
 *
 * Aceita string com ponto ou vírgula.
 *
 * @param amount - Valor em reais.
 * @returns Texto ``R$ X,XX`` ou string vazia se inválido.
 */
export function formatAmountToBrl(
  amount: string | number | null | undefined,
): string {
  if (amount == null || amount === '') {
    return '';
  }
  const normalized =
    typeof amount === 'number' ? amount.toString() : String(amount).trim();
  const cents = parseMoneyToCents(normalized);
  if (cents == null) {
    return '';
  }
  return formatCentsToBrl(cents);
}

/**
 * Converte texto monetário (reais) para centavos inteiros.
 *
 * Aceita ``1234,56``, ``1234.56``, ``1.234,56`` (BR) e ``1234``.
 * Rejeita valores inválidos, negativos ou com mais de duas casas.
 * String vazia → ``null`` (não NaN).
 *
 * @param input - Valor digitado ou string do backend.
 * @returns Centavos inteiros ou ``null`` se inválido.
 */
export function parseMoneyToCents(input: string | number): number | null {
  if (typeof input === 'number') {
    if (!Number.isFinite(input) || input < 0) {
      return null;
    }
    const scaled = Math.round(input * 100);
    if (Math.abs(input * 100 - scaled) > 1e-6) {
      return scaled >= 0 ? scaled : null;
    }
    return scaled;
  }

  let raw = String(input).trim();
  if (!raw) {
    return null;
  }
  raw = raw.replace(/R\$\s?/i, '').replace(/\s/g, '');

  if (raw.startsWith('-')) {
    return null;
  }

  // BR: 1.234,56 → remove milhares e troca vírgula
  if (raw.includes(',') && raw.includes('.')) {
    raw = raw.replace(/\./g, '').replace(',', '.');
  } else if (raw.includes(',')) {
    raw = raw.replace(',', '.');
  }

  if (!/^\d+(\.\d{1,2})?$/.test(raw)) {
    return null;
  }

  const [wholePart, fracPart = ''] = raw.split('.');
  const whole = Number.parseInt(wholePart, 10);
  if (!Number.isFinite(whole) || whole < 0) {
    return null;
  }
  const fracPadded = (fracPart + '00').slice(0, 2);
  const frac = Number.parseInt(fracPadded, 10);
  if (!Number.isFinite(frac) || frac < 0 || frac > 99) {
    return null;
  }
  return whole * 100 + frac;
}

/**
 * Resolve texto de mínimo de ativação a partir dos campos do backend.
 *
 * Prefere ``minimum_activation_amount``; senão formata centavos.
 * Não recalcula política localmente.
 * Moeda diferente de BRL → omite (retorna ``null``).
 *
 * @param amount - Valor em reais do backend (opcional).
 * @param cents - Valor em centavos do backend (opcional).
 * @param currency - Moeda ISO opcional (somente BRL suportada na v1).
 * @returns Texto BRL ou ``null`` se ausente/inválido/não-BRL.
 */
export function resolveMinimumActivationLabel(
  amount?: string | number | null,
  cents?: number | null,
  currency?: string | null,
): string | null {
  if (currency != null && currency !== '' && currency.toUpperCase() !== 'BRL') {
    return null;
  }
  if (amount != null && amount !== '') {
    const formatted = formatAmountToBrl(amount);
    if (formatted) {
      return formatted;
    }
  }
  if (cents != null) {
    const formatted = formatCentsToBrl(cents);
    if (formatted) {
      return formatted;
    }
  }
  return null;
}
