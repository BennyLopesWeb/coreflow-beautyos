/**
 * Utilitários para normalização e validação de telefone.
 */

/**
 * Remove caracteres não numéricos do telefone.
 *
 * @param valor - Telefone em qualquer formato.
 * @returns Apenas dígitos.
 */
export function normalizarTelefone(valor: string): string {
  return valor.replace(/\D/g, '');
}

/**
 * Verifica se dois telefones representam o mesmo número.
 *
 * @param a - Primeiro telefone.
 * @param b - Segundo telefone.
 * @returns True se os dígitos forem iguais.
 */
export function telefonesIguais(a: string, b: string): boolean {
  return normalizarTelefone(a) === normalizarTelefone(b);
}

/**
 * Valida telefone brasileiro (mínimo 10 dígitos).
 *
 * @param valor - Telefone informado.
 * @returns True se tiver ao menos 10 dígitos.
 */
export function telefoneValido(valor: string): boolean {
  return normalizarTelefone(valor).length >= 10;
}
