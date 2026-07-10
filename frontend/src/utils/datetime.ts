/**
 * Utilitários de data/hora para envio à API sem deslocamento UTC.
 */

/**
 * Formata Date no horário local como ISO sem timezone (YYYY-MM-DDTHH:mm:ss).
 * Evita que toISOString() altere o horário selecionado pelo usuário.
 *
 * @param date - Data/hora local selecionada.
 * @returns String ISO local para a API.
 */
export function formatLocalDateTime(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}:00`
  );
}
