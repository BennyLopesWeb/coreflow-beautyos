/**
 * DeepLinkService — parse custom scheme e universal links (CF-12/13).
 */
import * as Linking from 'expo-linking';
import { router } from 'expo-router';

const UNIVERSAL_HOST =
  process.env.EXPO_PUBLIC_UNIVERSAL_LINK_HOST ?? 'app.coreflow.app';

export interface ParsedDeepLink {
  tenantSlug: string;
  path: string;
  segments: string[];
  isUniversal: boolean;
}

/**
 * Extrai tenant e path de URL universal https://host/tenant/...
 *
 * @param url - URL HTTPS.
 * @returns ParsedDeepLink ou null.
 */
function parseUniversalLink(url: string): ParsedDeepLink | null {
  try {
    const parsed = new URL(url);
    if (parsed.hostname !== UNIVERSAL_HOST) {
      return null;
    }
    const segments = parsed.pathname.split('/').filter(Boolean);
    if (segments.length === 0) {
      return null;
    }
    const [tenantSlug, ...rest] = segments;
    const path = `/${rest.join('/')}`;
    return {
      tenantSlug,
      path,
      segments: rest,
      isUniversal: true,
    };
  } catch {
    return null;
  }
}

/**
 * Faz parse de URL custom scheme ``scheme://tenant/path/...``.
 *
 * @param url - URL completa (ex.: trancapro://salao-demo/bookings/42).
 * @returns Objeto parseado ou null se inválido.
 */
export function parseDeepLink(url: string): ParsedDeepLink | null {
  if (url.startsWith('https://') || url.startsWith('http://')) {
    return parseUniversalLink(url);
  }

  const parsed = Linking.parse(url);
  const hostname = parsed.hostname ?? '';
  const path = parsed.path ?? '';
  const tenantSlug = hostname || path.split('/').filter(Boolean)[0] || '';
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;

  if (!tenantSlug) {
    return null;
  }

  return {
    tenantSlug,
    path: normalizedPath,
    segments: normalizedPath.split('/').filter(Boolean),
    isUniversal: false,
  };
}

/**
 * Navega para rota Expo correspondente ao deep link.
 *
 * @param url - URL de deep link recebida (cold start, push ou universal link).
 * @returns void
 */
export function navigateFromDeepLink(url: string): void {
  const link = parseDeepLink(url);
  if (!link) {
    return;
  }

  const [section, id] = link.segments;

  if (section === 'bookings' || section === 'reservas' || section === 'consultas') {
    router.push('/(tabs)/agendamentos');
    return;
  }

  if (section === 'agendar' && id) {
    router.push(`/(tabs)/agendar/${id}`);
    return;
  }

  if (section === 'admin') {
    const adminSection = link.segments[1];
    if (adminSection === 'reservas') {
      router.push('/(admin)/reservas');
      return;
    }
  }

  if (section === 'agendamentos') {
    router.push('/(tabs)/agendamentos');
    return;
  }

  if (section === 'fila') {
    router.push('/(tabs)/fila');
  }
}

/**
 * Registra listener global de deep links (app aberto em background).
 *
 * @returns Função de cleanup para remover o listener.
 */
export function setupDeepLinkListener(): () => void {
  const subscription = Linking.addEventListener('url', ({ url }) => {
    navigateFromDeepLink(url);
  });

  Linking.getInitialURL().then((initialUrl) => {
    if (initialUrl) {
      navigateFromDeepLink(initialUrl);
    }
  });

  return () => subscription.remove();
}

/**
 * Monta URL de deep link custom scheme para um tenant.
 *
 * @param tenantSlug - Slug da empresa.
 * @param path - Caminho relativo (ex.: /bookings/42).
 * @param scheme - Scheme customizado (default trancapro).
 * @returns URL completa.
 */
export function buildDeepLink(
  tenantSlug: string,
  path: string,
  scheme = 'trancapro',
): string {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `${scheme}://${tenantSlug}${normalized}`;
}

/**
 * Monta universal link HTTPS para um tenant.
 *
 * @param tenantSlug - Slug da empresa.
 * @param path - Caminho relativo (ex.: /bookings/42).
 * @param host - Host universal (default app.coreflow.app).
 * @returns URL HTTPS completa.
 */
export function buildUniversalLink(
  tenantSlug: string,
  path: string,
  host = UNIVERSAL_HOST,
): string {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `https://${host}/${tenantSlug}${normalized}`;
}
