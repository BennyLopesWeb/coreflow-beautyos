/**
 * Resolução de registro de cliente para reservas e fila.
 */
import { clienteService } from '../services/clienteService';
import { Cliente } from '../types';

/**
 * Busca cliente pelo telefone ou cria um novo registro.
 *
 * @param nome - Nome completo do cliente.
 * @param telefone - Telefone informado ou confirmado.
 * @param email - E-mail opcional.
 * @returns Cliente existente ou recém-criado.
 */
export async function obterOuCriarCliente(
  nome: string,
  telefone: string,
  email?: string,
): Promise<Cliente> {
  const existente = await clienteService.buscarPorTelefone(telefone);
  if (existente) {
    return existente;
  }
  return clienteService.criar({
    nome: nome.trim(),
    telefone: telefone.trim(),
    email: email?.trim() || undefined,
  });
}
