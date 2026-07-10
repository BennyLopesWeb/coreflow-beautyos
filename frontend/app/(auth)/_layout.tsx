import { Stack } from 'expo-router';
import { AuthGuard } from '../../src/components/AuthGuard';

export default function AuthLayout() {
  return (
    <AuthGuard requireAuth={false} redirectTo="/(tabs)/dashboard">
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="login" />
        <Stack.Screen name="register" />
      </Stack>
    </AuthGuard>
  );
}

