/**
 * PushNotificationService — Expo Notifications nativo + fallback mock (CF-14).
 */
import Constants from 'expo-constants';
import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import api from '../config/api';
import { navigateFromDeepLink } from './deepLinkService';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

/**
 * Indica se push está habilitado no frontend.
 *
 * @returns true se EXPO_PUBLIC_PUSH_ENABLED não for false.
 */
export function isPushEnabled(): boolean {
  const flag = process.env.EXPO_PUBLIC_PUSH_ENABLED;
  return flag !== 'false' && flag !== '0';
}

/**
 * Indica se deve usar token Expo nativo (dispositivo físico iOS/Android).
 *
 * @returns true em device físico com push habilitado.
 */
export function shouldUseNativePushToken(): boolean {
  return isPushEnabled() && Device.isDevice && Platform.OS !== 'web';
}

/**
 * Gera token mock para desenvolvimento (ExponentPushToken[dev-...]).
 *
 * @param userId - ID do usuário autenticado.
 * @returns Token simulado compatível com backend.
 */
export function buildMockPushToken(userId: number): string {
  return `ExponentPushToken[dev-user-${userId}]`;
}

/**
 * Solicita permissões e obtém token Expo Push nativo.
 *
 * @returns Token Expo ou null se indisponível (simulador/web/negado).
 */
export async function obtainExpoPushToken(): Promise<string | null> {
  if (!shouldUseNativePushToken()) {
    return null;
  }

  const { status: existing } = await Notifications.getPermissionsAsync();
  let finalStatus = existing;
  if (existing !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }
  if (finalStatus !== 'granted') {
    return null;
  }

  const projectId =
    process.env.EXPO_PUBLIC_EAS_PROJECT_ID ??
    Constants.expoConfig?.extra?.eas?.projectId;

  try {
    const token = await Notifications.getExpoPushTokenAsync(
      projectId ? { projectId } : undefined,
    );
    return token.data;
  } catch {
    return null;
  }
}

/**
 * Registra token push no backend CoreFlow v1.
 *
 * Usa token nativo em device físico; fallback mock em dev/simulador.
 *
 * @param userId - ID do usuário logado.
 * @returns Resposta da API ou null se push desabilitado.
 */
export async function registerDevicePushToken(
  userId: number,
): Promise<{ id: number; expo_push_token: string } | null> {
  if (!isPushEnabled()) {
    return null;
  }

  const nativeToken = await obtainExpoPushToken();
  const expoPushToken = nativeToken ?? buildMockPushToken(userId);
  const platform =
    Platform.OS === 'ios'
      ? 'ios'
      : Platform.OS === 'android'
        ? 'android'
        : 'web';

  const response = await api.post('/v1/devices/register', {
    expo_push_token: expoPushToken,
    platform,
  });

  return response.data;
}

/**
 * Configura listeners de push — abre deep link ao tocar na notificação.
 *
 * @returns Função cleanup para remover listeners.
 */
export function setupPushNotificationListeners(): () => void {
  const receivedSub = Notifications.addNotificationReceivedListener(() => undefined);

  const responseSub = Notifications.addNotificationResponseReceivedListener((response) => {
    const data = response.notification.request.content.data;
    const link =
      (typeof data?.universal_link === 'string' && data.universal_link) ||
      (typeof data?.deep_link === 'string' && data.deep_link);
    if (link) {
      navigateFromDeepLink(link);
    }
  });

  return () => {
    receivedSub.remove();
    responseSub.remove();
  };
}

export const pushNotificationService = {
  isPushEnabled,
  shouldUseNativePushToken,
  buildMockPushToken,
  obtainExpoPushToken,
  registerDevicePushToken,
  setupPushNotificationListeners,
};
