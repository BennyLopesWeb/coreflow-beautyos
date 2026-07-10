/**
 * Utilitários de formatação para exibição de tranças.
 */
import { PERCENTUAL_SINAL } from '../constants/tranca';

/**
 * Formata duração em minutos para texto legível (ex: "2h 30min").
 *
 * @param {number} minutos - Duração total em minutos.
 * @returns {string} Texto formatado da duração.
 */
export function formatarDuracao(minutos: number): string {
  const horas = Math.floor(minutos / 60);
  const mins = minutos % 60;
  const partes: string[] = [];
  if (horas > 0) partes.push(`${horas}h`);
  if (mins > 0) partes.push(`${mins}min`);
  return partes.join(' ') || '0min';
}

/**
 * Formata valor decimal/string para moeda brasileira.
 *
 * @param {string | number} valor - Valor numérico ou string.
 * @returns {string} Valor formatado (ex: "R$ 140,00").
 */
export function formatarMoeda(valor: string | number): string {
  const num = typeof valor === 'string' ? parseFloat(valor) : valor;
  return `R$ ${num.toFixed(2).replace('.', ',')}`;
}

/**
 * Calcula sinal de entrada a partir do valor total e percentual do modelo.
 *
 * @param {string | number} valorTotal - Valor total do serviço.
 * @param {string | number | undefined} percentual - Fração decimal (ex: 0.3). Usa padrão se omitido.
 * @returns {number} Valor do sinal arredondado em centavos.
 */
export function calcularSinal(
  valorTotal: string | number,
  percentual?: string | number,
): number {
  const total = typeof valorTotal === 'string' ? parseFloat(valorTotal) : valorTotal;
  const pct = percentual != null
    ? (typeof percentual === 'string' ? parseFloat(percentual) : percentual)
    : PERCENTUAL_SINAL;
  return Math.round(total * pct * 100) / 100;
}

/**
 * Retorna texto do percentual do sinal (ex: "30%").
 *
 * @param {string | number | undefined} percentual - Fração decimal opcional do modelo.
 * @returns {string} Percentual formatado para exibição.
 */
export function labelPercentualSinal(percentual?: string | number): string {
  const pct = percentual != null
    ? (typeof percentual === 'string' ? parseFloat(percentual) : percentual)
    : PERCENTUAL_SINAL;
  return `${Math.round(pct * 100)}%`;
}
