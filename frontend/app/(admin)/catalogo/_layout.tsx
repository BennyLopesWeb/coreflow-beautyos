import { Stack } from 'expo-router';

/**
 * Stack de navegação do catálogo admin (lista → álbum).
 */
export default function CatalogoLayout() {
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: '#7B2CBF' },
        headerTintColor: '#FFF',
      }}
    >
      <Stack.Screen name="index" options={{ title: 'Catálogo' }} />
      <Stack.Screen name="novo" options={{ title: 'Novo tipo' }} />
      <Stack.Screen name="[id]" options={{ title: 'Gerenciar tipo' }} />
    </Stack>
  );
}
