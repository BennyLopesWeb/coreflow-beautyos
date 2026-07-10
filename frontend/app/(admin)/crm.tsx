import React, { useCallback, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  RefreshControl,
} from 'react-native';
import { useFocusEffect } from 'expo-router';
import { adminService } from '../../src/services/adminService';
import { ClienteCrm } from '../../src/types';
import { Loader } from '../../src/components/Loader';

/**
 * Retorna cor do badge conforme status CRM.
 */
function statusColor(status: string): string {
  const map: Record<string, string> = {
    novo: '#3498DB',
    ativo: '#27AE60',
    inativo: '#E74C3C',
    pendente_pagamento: '#F39C12',
  };
  return map[status] || '#999';
}

/**
 * Formata label legível do status CRM.
 */
function statusLabel(status: string): string {
  const map: Record<string, string> = {
    novo: 'Novo',
    ativo: 'Ativo',
    inativo: 'Inativo',
    pendente_pagamento: 'Pend. pagamento',
  };
  return map[status] || status;
}

/**
 * Tela CRM admin — fluxo de clientes e segmentação.
 */
export default function AdminCrmScreen() {
  const [clientes, setClientes] = useState<ClienteCrm[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async () => {
    try {
      const data = await adminService.listarCrm();
      setClientes(data);
    } catch (error) {
      console.error('Erro ao carregar CRM:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      loadData();
    }, []),
  );

  if (loading) {
    return <Loader message="Carregando CRM..." />;
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={clientes}
        keyExtractor={(item) => String(item.id)}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadData(); }} />
        }
        ListEmptyComponent={
          <Text style={styles.empty}>Nenhum cliente cadastrado.</Text>
        }
        renderItem={({ item }) => (
          <View style={styles.card}>
            <View style={styles.cardHeader}>
              <Text style={styles.nome}>{item.nome}</Text>
              <View style={[styles.badge, { backgroundColor: statusColor(item.status_crm) + '22' }]}>
                <Text style={[styles.badgeText, { color: statusColor(item.status_crm) }]}>
                  {statusLabel(item.status_crm)}
                </Text>
              </View>
            </View>
            <Text style={styles.telefone}>{item.telefone}</Text>
            <View style={styles.stats}>
              <Text style={styles.stat}>
                {item.total_agendamentos} agendamento(s)
              </Text>
              <Text style={styles.stat}>
                Gasto: R$ {parseFloat(item.total_gasto).toFixed(2).replace('.', ',')}
              </Text>
            </View>
            {item.ultima_visita && (
              <Text style={styles.ultima}>
                Última visita: {new Date(item.ultima_visita).toLocaleDateString('pt-BR')}
              </Text>
            )}
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5' },
  empty: { textAlign: 'center', color: '#888', marginTop: 40 },
  card: {
    backgroundColor: '#FFF',
    marginHorizontal: 16,
    marginVertical: 6,
    padding: 16,
    borderRadius: 10,
  },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  nome: { fontSize: 16, fontWeight: '600', flex: 1 },
  telefone: { fontSize: 14, color: '#666', marginTop: 4 },
  stats: { flexDirection: 'row', gap: 16, marginTop: 10 },
  stat: { fontSize: 13, color: '#555' },
  ultima: { fontSize: 12, color: '#999', marginTop: 6 },
  badge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  badgeText: { fontSize: 11, fontWeight: '600' },
});
