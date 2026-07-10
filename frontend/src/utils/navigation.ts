/**
 * Utilitários de navegação Expo Router.
 */
import { useRouter } from 'expo-router';

type AppRouter = ReturnType<typeof useRouter>;

/**
 * Navega para a tela de agendamento com categoria e modelo pré-selecionados.
 *
 * Usa URL explícita (mais confiável no web estático) com query `imagemId`.
 *
 * @param router - Instância do router Expo.
 * @param trancaId - ID da categoria.
 * @param imagemId - ID do modelo (service_image).
 */
export function irParaAgendar(router: AppRouter, trancaId: number, imagemId: number): void {
  router.push(`/(tabs)/agendar/${trancaId}?imagemId=${imagemId}`);
}

/**
 * Navega para detalhes do modelo.
 *
 * @param router - Instância do router Expo.
 * @param trancaId - ID da categoria.
 * @param imagemId - ID do modelo.
 */
export function irParaDetalheModelo(router: AppRouter, trancaId: number, imagemId: number): void {
  router.push(`/(tabs)/detalhe/${trancaId}/modelo/${imagemId}`);
}
