/**
 * Cliente HTTP da política administrativa de booking (grupo activation).
 */
import api from '../config/api';

/** Modos de política de entrada (espelha contrato backend). */
export type ActivationModeV1 = 'percentage_with_cap' | 'tiered_percentage';

/** Grupo activation. */
export interface ActivationPolicyV1 {
  mode: ActivationModeV1;
  currency?: 'BRL' | string;
  percentage?: number | null;
  cap_cents?: number | null;
  standard_percentage?: number | null;
  high_value_threshold_cents?: number | null;
  high_value_percentage?: number | null;
}

/** Resposta GET/PUT/PATCH/DELETE /admin/booking-policy. */
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

/** Body PATCH — sem company_id. */
export interface BookingPolicyOverrideRequestV1 {
  activation?: ActivationPolicyV1;
  expected_version?: number;
  reason: string;
}

export const bookingPolicyService = {
  /**
   * Obtém a política efetiva do tenant autenticado.
   *
   * @returns Resposta administrativa completa.
   */
  obter: async (): Promise<BookingPolicyAdminResponseV1> => {
    const response = await api.get<BookingPolicyAdminResponseV1>(
      '/admin/booking-policy',
    );
    return response.data;
  },

  /**
   * Mescla patch no override (PATCH). Não envia ``company_id``.
   *
   * @param body - activation + reason + expected_version.
   * @returns Política efetiva após persistir.
   */
  atualizarActivation: async (
    body: BookingPolicyOverrideRequestV1,
  ): Promise<BookingPolicyAdminResponseV1> => {
    const payload: BookingPolicyOverrideRequestV1 = {
      activation: body.activation,
      reason: body.reason,
    };
    if (body.expected_version != null) {
      payload.expected_version = body.expected_version;
    }
    const response = await api.patch<BookingPolicyAdminResponseV1>(
      '/admin/booking-policy',
      payload,
    );
    return response.data;
  },
};
