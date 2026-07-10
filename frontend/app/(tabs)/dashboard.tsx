import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../src/contexts/AuthContext';
import { agendamentoService } from '../../src/services/agendamentoService';
import { filaService } from '../../src/services/filaService';
import { Agendamento } from '../../src/types';
import { Loader } from '../../src/components/Loader';

/**
 * Card de ação rápida no dashboard.
 */
function ActionCard({
  icon,
  title,
  subtitle,
  color,
  onPress,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  subtitle: string;
  color: string;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity style={[styles.actionCard, { borderLeftColor: color }]} onPress={onPress}>
      <View style={[styles.actionIcon, { backgroundColor: color }]}>
        <Ionicons name={icon} size={24} color="#FFF" />
      </View>
      <View style={styles.actionText}>
        <Text style={styles.actionTitle}>{title}</Text>
        <Text style={styles.actionSubtitle}>{subtitle}</Text>
      </View>
      <Ionicons name="chevron-forward" size={20} color="#CCC" />
    </TouchableOpacity>
  );
}

/**
 * Tela inicial com atalhos para agendar, fila e agendamentos.
 */
export default function DashboardScreen() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [agendamentos, setAgendamentos] = useState<Agendamento[]>([]);
  const [totalFila, setTotalFila] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const hoje = new Date().toISOString().split('T')[0];
      const [agendamentosData, filaData] = await Promise.all([
        agendamentoService.listar(),
        filaService.consultar(hoje),
      ]);
      setAgendamentos(agendamentosData.slice(0, 3));
      setTotalFila(filaData.total_pessoas);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <Loader message="Carregando..." />;
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>Olá, {user?.nome || user?.email}</Text>
          <Text style={styles.subtitle}>O que deseja fazer?</Text>
        </View>
        <TouchableOpacity onPress={logout} style={styles.logoutBtn}>
          <Ionicons name="log-out-outline" size={22} color="#7B2CBF" />
        </TouchableOpacity>
      </View>

      <View style={styles.actions}>
        <ActionCard
          icon="calendar-outline"
          title="Agendar Serviço"
          subtitle="Escolha uma trança e reserve horário"
          color="#7B2CBF"
          onPress={() => router.push('/(tabs)/catalogo')}
        />
        <ActionCard
          icon="people-outline"
          title="Ver Fila de Hoje"
          subtitle={`${totalFila} pessoa(s) aguardando`}
          color="#E67E22"
          onPress={() => router.push('/(tabs)/fila')}
        />
        <ActionCard
          icon="list-outline"
          title="Meus Agendamentos"
          subtitle="Consulte e entre na fila"
          color="#27AE60"
          onPress={() => router.push('/(tabs)/agendamentos')}
        />
      </View>

      {agendamentos.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Próximos Agendamentos</Text>
          {agendamentos.map((ag) => (
            <View key={ag.id} style={styles.agendamentoItem}>
              <Text style={styles.agendamentoNome}>
                {ag.cliente?.nome || `Agendamento #${ag.id}`}
              </Text>
              <Text style={styles.agendamentoData}>
                {new Date(ag.data_hora).toLocaleString('pt-BR')}
              </Text>
              <Text style={styles.agendamentoStatus}>{ag.status}</Text>
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: 24,
    backgroundColor: '#FFF',
    marginBottom: 16,
  },
  greeting: {
    fontSize: 24,
    fontWeight: '700',
    color: '#333',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
  },
  logoutBtn: {
    padding: 8,
  },
  actions: {
    paddingHorizontal: 16,
    gap: 12,
    marginBottom: 16,
  },
  actionCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    borderLeftWidth: 4,
  },
  actionIcon: {
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 14,
  },
  actionText: {
    flex: 1,
  },
  actionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#333',
  },
  actionSubtitle: {
    fontSize: 13,
    color: '#666',
    marginTop: 2,
  },
  card: {
    backgroundColor: '#FFF',
    marginHorizontal: 16,
    marginBottom: 24,
    padding: 20,
    borderRadius: 12,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#333',
    marginBottom: 16,
  },
  agendamentoItem: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  agendamentoNome: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  agendamentoData: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  agendamentoStatus: {
    fontSize: 12,
    color: '#7B2CBF',
    textTransform: 'uppercase',
  },
});
