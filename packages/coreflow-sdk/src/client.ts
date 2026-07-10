/**
 * CoreFlowClient — cliente HTTP tipado para API CoreFlow v1.
 */
import type {
  AvailabilityQuery,
  AvailabilitySlot,
  BookingCreateV1,
  BookingV1,
  CatalogV1,
  MarketplaceListingV1,
  OfferingV1,
  PluginConfigV1,
} from './types';

/**
 * Contrato mínimo HTTP compatível com Axios (evita conflito de versões entre pacotes).
 */
export interface CoreFlowHttpClient {
  get<T>(url: string, config?: { params?: Record<string, unknown> }): Promise<{ data: T }>;
  post<T>(url: string, body?: unknown): Promise<{ data: T }>;
}

/**
 * Cliente SDK CoreFlow Platform.
 *
 * Encapsula rotas v1 declaradas em ``manifest.yaml`` → ``sdk.routes``.
 * Reutiliza instância Axios do app (interceptors de auth inclusos).
 *
 * @param http - Instância HTTP configurada (baseURL, tokens).
 */
export class CoreFlowClient {
  private catalogCache: CatalogV1[] | null = null;

  /**
   * @param http - Cliente HTTP do aplicativo (Axios ou compatível).
   */
  constructor(private readonly http: CoreFlowHttpClient) {}

  /**
   * Invalida cache local de catálogos.
   *
   * @returns {void}
   */
  invalidateCatalogCache(): void {
    this.catalogCache = null;
  }

  /**
   * Lista catálogos v1 do tenant.
   *
   * @returns {Promise<CatalogV1[]>} Catálogos CoreFlow.
   */
  async listCatalogs(forceRefresh = false): Promise<CatalogV1[]> {
    if (!this.catalogCache || forceRefresh) {
      const response = await this.http.get<CatalogV1[]>('/v1/catalogs');
      this.catalogCache = response.data;
    }
    return this.catalogCache ?? [];
  }

  /**
   * Lista offerings de um catálogo.
   *
   * @param catalogId - ID core_catalogs.
   * @returns {Promise<OfferingV1[]>} Ofertas do catálogo.
   */
  async listOfferings(catalogId: number): Promise<OfferingV1[]> {
    const response = await this.http.get<OfferingV1[]>(
      `/v1/catalogs/${catalogId}/offerings`,
    );
    return response.data;
  }

  /**
   * Resolve IDs genéricos a partir de IDs legados BeautyOS.
   *
   * @param trancaId - ID legado tranca.
   * @param serviceImageId - ID legado service_image opcional.
   * @returns {Promise<{ catalogId: number; offeringId: number }>} IDs CoreFlow.
   */
  async resolveLegacyIds(
    trancaId: number,
    serviceImageId?: number,
  ): Promise<{ catalogId: number; offeringId: number }> {
    const catalogs = await this.listCatalogs();
    const catalog = catalogs.find((c) => c.legacy_tranca_id === trancaId);
    if (!catalog) {
      throw new Error(`Catalog não encontrado para tranca ${trancaId}`);
    }
    const offerings = await this.listOfferings(catalog.id);
    const offering = serviceImageId != null
      ? offerings.find((o) => o.legacy_service_image_id === serviceImageId)
      : offerings[0];
    if (!offering) {
      throw new Error(`Offering não encontrado para modelo ${serviceImageId ?? 'default'}`);
    }
    return { catalogId: catalog.id, offeringId: offering.id };
  }

  /**
   * Consulta disponibilidade via scheduling engine v1.
   *
   * @param query - Data, catalog e offering.
   * @returns {Promise<AvailabilitySlot[]>} Slots disponíveis.
   */
  async getAvailability(query: AvailabilityQuery): Promise<AvailabilitySlot[]> {
    const response = await this.http.get<AvailabilitySlot[]>(
      '/v1/scheduling/availability',
      {
        params: {
          date: query.date,
          catalog_id: query.catalog_id,
          offering_id: query.offering_id,
        },
      },
    );
    return response.data;
  }

  /**
   * Cria booking genérico via CQRS v1.
   *
   * @param body - Dados do booking.
   * @returns {Promise<BookingV1>} Booking criado.
   */
  async createBooking(body: BookingCreateV1): Promise<BookingV1> {
    const response = await this.http.post<BookingV1>('/v1/bookings', body);
    return response.data;
  }

  /**
   * Obtém configuração de plugin para um tenant (terminologia UI).
   *
   * @param companySlug - Slug da empresa.
   * @returns {Promise<PluginConfigV1>} Config do plugin ativo.
   */
  async getPluginConfig(companySlug: string): Promise<PluginConfigV1> {
    const response = await this.http.get<PluginConfigV1>(
      `/v1/plugins/config/by-company/${companySlug}`,
    );
    return response.data;
  }

  /**
   * Lista plugins do marketplace cloud + locais.
   *
   * @returns {Promise<MarketplaceListingV1[]>} Catálogo marketplace.
   */
  async listMarketplaceListings(): Promise<MarketplaceListingV1[]> {
    const response = await this.http.get<MarketplaceListingV1[]>(
      '/v1/marketplace/listings',
    );
    return response.data;
  }

  /**
   * Instala/ativa plugin no tenant atual (admin).
   *
   * @param pluginId - ID do plugin.
   * @returns {Promise<{ plugin_id: string; message: string }>} Confirmação.
   */
  async installPlugin(
    pluginId: string,
  ): Promise<{ plugin_id: string; message: string }> {
    const response = await this.http.post<{ plugin_id: string; message: string }>(
      '/v1/marketplace/install',
      { plugin_id: pluginId },
    );
    return response.data;
  }
}
