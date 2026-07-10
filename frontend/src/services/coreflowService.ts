/**
 * Service CoreFlow v1 — delega ao @coreflow/sdk (CF-11).
 */
import { CoreFlowClient } from '@coreflow/sdk';
import api from '../config/api';
import {
  Agendamento,
  AgendamentoCreate,
  HorarioDisponivel,
} from '../types';

const sdk = new CoreFlowClient(api);

/**
 * Indica se o frontend deve preferir API CoreFlow v1.
 * Default: true. Defina EXPO_PUBLIC_USE_COREFLOW_V1=false para forçar legado.
 */
export function useCoreflowV1(): boolean {
  const flag = process.env.EXPO_PUBLIC_USE_COREFLOW_V1;
  if (flag === 'false' || flag === '0') {
    return false;
  }
  return true;
}

/**
 * Invalida cache local de catálogos (após CRUD admin).
 */
export function invalidateCatalogCache(): void {
  sdk.invalidateCatalogCache();
}

/**
 * Resolve IDs genéricos a partir de IDs legados (tranca / service_image).
 */
export const resolveLegacyIds = sdk.resolveLegacyIds.bind(sdk);

/**
 * Consulta disponibilidade via scheduling engine CoreFlow v1.
 */
export async function consultarDisponibilidadeV1(
  data: string,
  trancaId: number,
  serviceImageId?: number,
): Promise<HorarioDisponivel[]> {
  const { catalogId, offeringId } = await sdk.resolveLegacyIds(trancaId, serviceImageId);
  const slots = await sdk.getAvailability({
    date: `${data}T08:00:00`,
    catalog_id: catalogId,
    offering_id: offeringId,
  });
  return slots.map((slot) => ({
    horario: formatHorario(slot.starts_at),
    disponivel: slot.available,
  }));
}

/**
 * Formata datetime ISO para HH:MM (locale pt-BR).
 */
function formatHorario(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso.slice(11, 16);
  }
  return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

/**
 * Cria booking via API CoreFlow v1 (CQRS + metamodelo).
 */
export async function criarBookingV1(data: AgendamentoCreate): Promise<Agendamento> {
  const { catalogId, offeringId } = await sdk.resolveLegacyIds(
    data.tranca_id,
    data.service_image_id,
  );

  const body = await sdk.createBooking({
    customer_id: data.cliente_id,
    catalog_id: catalogId,
    offering_id: offeringId,
    scheduled_at: data.data_hora,
    notes: data.observacoes,
  });

  const agendamentoId = body.legacy_agendamento_id ?? body.id;

  return {
    id: agendamentoId,
    cliente_id: body.customer_id,
    tranca_id: data.tranca_id,
    service_image_id: data.service_image_id,
    data_hora: body.scheduled_at,
    sinal_pago: body.deposit_paid ?? false,
    status: body.status as Agendamento['status'],
    status_pagamento: body.payment_status as Agendamento['status_pagamento'],
    valor_total_reserva: String(body.price_total),
    valor_sinal_reserva: String(body.deposit_amount),
    observacoes: body.notes ?? undefined,
  };
}

export const coreflowService = {
  useCoreflowV1,
  invalidateCatalogCache,
  resolveLegacyIds,
  consultarDisponibilidadeV1,
  criarBookingV1,
  listCatalogs: () => sdk.listCatalogs(),
  getPluginConfig: (slug: string) => sdk.getPluginConfig(slug),
  listMarketplaceListings: () => sdk.listMarketplaceListings(),
  installPlugin: (pluginId: string) => sdk.installPlugin(pluginId),
  client: sdk,
};
