/**
 * Feature flags via ``EXPO_PUBLIC_*`` (padrão Expo do projeto).
 */

/**
 * Controla a tela administrativa de política de entrada.
 *
 * Default: habilitada. Defina ``EXPO_PUBLIC_DEPOSIT_POLICY_UI=false`` para ocultar.
 * Quote/booking/confirmação não dependem desta flag.
 *
 * @returns True se a UI admin de activation deve aparecer.
 */
export function isDepositPolicyUiEnabled(): boolean {
  const flag = process.env.EXPO_PUBLIC_DEPOSIT_POLICY_UI;
  if (flag === undefined || flag === '') {
    return true;
  }
  return flag !== 'false' && flag !== '0';
}
