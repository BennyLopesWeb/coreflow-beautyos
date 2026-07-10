/**
 * Root Layout
 * Configuração principal do Expo Router
 */
import 'react-native-gesture-handler';
import { useEffect } from 'react';
import { Stack } from 'expo-router';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { AuthProvider } from '../src/contexts/AuthContext';
import { setupDeepLinkListener } from '../src/services/deepLinkService';
import { setupPushNotificationListeners } from '../src/services/pushNotificationService';

export default function RootLayout() {
  useEffect(() => {
    const cleanupDeepLink = setupDeepLinkListener();
    const cleanupPush = setupPushNotificationListeners();
    return () => {
      cleanupDeepLink();
      cleanupPush();
    };
  }, []);

  return (
    <SafeAreaProvider>
      <AuthProvider>
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="index" />
          <Stack.Screen name="(auth)" />
          <Stack.Screen name="(tabs)" />
          <Stack.Screen name="(admin)" />
        </Stack>
      </AuthProvider>
    </SafeAreaProvider>
  );
}
