import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { AdminGuard } from '../../src/components/AdminGuard';
import {
  AdminOperacionalProvider,
  useAdminOperacionalContext,
  formatTabBadge,
} from '../../src/contexts/AdminOperacionalContext';

/**
 * Tabs admin com badges de pendências em Reservas e Fila.
 */
function AdminTabs() {
  const { reservas, fila } = useAdminOperacionalContext();

  return (
    <Tabs
      screenOptions={{
        headerShown: true,
        tabBarActiveTintColor: '#7B2CBF',
        tabBarInactiveTintColor: '#999',
        tabBarStyle: { paddingBottom: 4, height: 60 },
        headerStyle: { backgroundColor: '#7B2CBF' },
        headerTintColor: '#FFF',
      }}
    >
      <Tabs.Screen
        name="catalogo"
        options={{
          title: 'Catálogo',
          headerShown: false,
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="images" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="dashboard"
        options={{
          title: 'Painel',
          headerShown: false,
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="grid" size={size} color={color} />
          ),
          tabBarBadge: formatTabBadge(reservas.length + fila.length),
        }}
      />
      <Tabs.Screen
        name="reservas"
        options={{
          title: 'Reservas',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="bookmark" size={size} color={color} />
          ),
          tabBarBadge: formatTabBadge(reservas.length),
        }}
      />
      <Tabs.Screen
        name="pagamentos"
        options={{
          title: 'Pagamentos',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="card" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="agenda"
        options={{
          title: 'Agenda',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="calendar" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="fila"
        options={{
          title: 'Fila',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="people" size={size} color={color} />
          ),
          tabBarBadge: formatTabBadge(fila.length),
        }}
      />
      <Tabs.Screen
        name="fila-operacional"
        options={{
          title: 'Atendimento',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="cut" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="crm"
        options={{
          title: 'CRM',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="person-circle" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="agente"
        options={{
          title: 'Agente IA',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="sparkles" size={size} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}

export default function AdminLayout() {
  return (
    <AdminGuard>
      <AdminOperacionalProvider>
        <AdminTabs />
      </AdminOperacionalProvider>
    </AdminGuard>
  );
}
