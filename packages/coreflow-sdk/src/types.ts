/**
 * Tipos públicos do CoreFlow SDK TypeScript.
 */

/** Catálogo genérico CoreFlow v1. */
export interface CatalogV1 {
  id: number;
  company_id: number;
  name: string;
  slug: string;
  legacy_tranca_id?: number | null;
  active: boolean;
}

/** Oferta/modelo genérico CoreFlow v1. */
export interface OfferingV1 {
  id: number;
  catalog_id: number;
  company_id?: number;
  name?: string | null;
  description?: string | null;
  price_total?: string | null;
  deposit_pct?: string | null;
  /** Cotação comercial do sinal — não é valor pago nem necessariamente o mínimo. */
  deposit_amount?: string | null;
  legacy_service_image_id?: number | null;
  duration_minutes?: number | null;
  image_url?: string | null;
  active: boolean;
  currency?: string;
  /** Mínimo de ativação em centavos (backend). */
  minimum_activation_cents?: number | null;
  /** Mínimo de ativação em reais (backend). */
  minimum_activation_amount?: string | null;
}

/** Slot de disponibilidade do scheduling engine. */
export interface AvailabilitySlot {
  starts_at: string;
  available: boolean;
  duration_minutes?: number | null;
  catalog_id: number;
  offering_id: number;
  resource_id?: number | null;
  worker_id?: number | null;
}

/** Booking genérico CoreFlow v1. */
export interface BookingV1 {
  id: number;
  company_id?: number;
  legacy_agendamento_id?: number | null;
  customer_id: number;
  catalog_id: number;
  offering_id: number;
  scheduled_at: string;
  status: string;
  payment_status: string;
  price_total: string;
  /** Cotação comercial do sinal — não é valor pago. */
  deposit_amount: string;
  deposit_paid: boolean;
  remaining_amount?: string;
  notes?: string | null;
  currency?: string;
  /** Mínimo de ativação em centavos (backend / snapshot). */
  minimum_activation_cents?: number | null;
  /** Mínimo de ativação em reais (backend). */
  minimum_activation_amount?: string | null;
}

/** Modos de política de entrada (CONFIG-DEPOSIT-POLICY-01). */
export type ActivationModeV1 = 'percentage_with_cap' | 'tiered_percentage';

/** Grupo ``activation`` da BookingPolicy. */
export interface ActivationPolicyV1 {
  mode: ActivationModeV1;
  currency?: 'BRL' | string;
  percentage?: number | null;
  cap_cents?: number | null;
  standard_percentage?: number | null;
  high_value_threshold_cents?: number | null;
  high_value_percentage?: number | null;
}

/** Resposta de ``GET/PUT/PATCH/DELETE /admin/booking-policy``. */
export interface BookingPolicyAdminResponseV1 {
  company_id: number;
  has_active_override: boolean;
  source: 'default' | 'override';
  policy: {
    activation?: ActivationPolicyV1;
    [key: string]: unknown;
  };
  override?: Record<string, unknown> | null;
  version?: number | null;
  updated_at?: string | null;
}

/** Body de PUT/PATCH ``/admin/booking-policy`` (sem company_id). */
export interface BookingPolicyOverrideRequestV1 {
  activation?: ActivationPolicyV1;
  expected_version?: number;
  reason: string;
}

/** Body para criação de booking v1. */
export interface BookingCreateV1 {
  customer_id: number;
  catalog_id: number;
  offering_id: number;
  scheduled_at: string;
  notes?: string | null;
}

/** Configuração de plugin por tenant. */
export interface PluginConfigV1 {
  company_id: number;
  company_slug: string;
  plugin_id: string;
  product_name: string;
  terminology: Record<string, string>;
  features: string[];
  deep_links?: {
    scheme: string;
    universal_host?: string;
    prefix?: string;
    routes: Record<string, string>;
  };
}

/** Listing do marketplace CoreFlow. */
export interface MarketplaceListingV1 {
  plugin_id: string;
  name: string;
  version: string;
  description?: string;
  product_name?: string;
  source: string;
  installable: boolean;
  pricing?: string;
  min_platform_version?: string;
  installed?: boolean;
  available_locally?: boolean;
  local_version?: string | null;
}

/** Parâmetros de consulta de disponibilidade. */
export interface AvailabilityQuery {
  date: string;
  catalog_id: number;
  offering_id: number;
}
