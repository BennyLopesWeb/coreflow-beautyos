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
  name?: string | null;
  legacy_service_image_id?: number | null;
  duration_minutes?: number | null;
  active: boolean;
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
  legacy_agendamento_id?: number | null;
  customer_id: number;
  catalog_id: number;
  offering_id: number;
  scheduled_at: string;
  status: string;
  payment_status: string;
  price_total: string;
  deposit_amount: string;
  deposit_paid: boolean;
  remaining_amount?: string;
  notes?: string | null;
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
