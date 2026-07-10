import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { AuthGuard } from '../../src/components/AuthGuard';

export default function TabsLayout() {
  return (
    <AuthGuard requireAuth={true} redirectTo="/(auth)/login">
      <Tabs
        screenOptions={{
          headerShown: true,
          tabBarActiveTintColor: '#7B2CBF',
          tabBarInactiveTintColor: '#999',
          tabBarStyle: { paddingBottom: 4, height: 60 },
        }}
      >
        <Tabs.Screen
          name="dashboard"
          options={{
            title: 'Início',
            headerShown: false,
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="home" size={size} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="catalogo"
          options={{
            title: 'Agendar',
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="calendar" size={size} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="agendamentos"
          options={{
            title: 'Agenda',
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="list" size={size} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="fila"
          options={{
            title: 'Fila',
            headerShown: false,
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="people" size={size} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="agendar/[id]"
          options={{ href: null }}
        />
        <Tabs.Screen
          name="detalhe/[id]"
          options={{ href: null }}
        />
        <Tabs.Screen
          name="detalhe/[id]/modelo/[imagemId]"
          options={{ href: null, title: 'Detalhes do modelo' }}
        />
        <Tabs.Screen
          name="clientes"
          options={{ href: null }}
        />
        <Tabs.Screen
          name="financeiro"
          options={{ href: null }}
        />
      </Tabs>
    </AuthGuard>
  );
}
