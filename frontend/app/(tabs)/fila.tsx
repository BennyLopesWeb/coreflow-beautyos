import React, { useCallback, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  RefreshControl,
} from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { filaService } from '../../src/services/filaService';
import { FilaItem, StatusFila } from '../../src/types';
import { Loader } from '../../src/components/Loader';
import { ButtonPrimary } from '../../src/components/ButtonPrimary';

const STATUS_LABEL: Record<StatusFila, string> = {
  waiting: 'Aguardando',
  contacted: 'Em contato',
  approved: 'Aprovado',
  rejected: 'Rejeitado',
  cancelled: 'Cancelado',
};

/**
 * Tela de visualização da fila de espera do dia (FIFO).
 */
export default function FilaScreen() {
  const router = useRouter();
  const dataFila = new Date().toISOString().split('T')[0];
  const [fila, setFila] = useState<FilaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async () => {
    try {
      const filaData = await filaService.consultar(dataFila);
      setFila(filaData.posicoes);
    } catch (error) {
      console.error('Erro ao carregar fila:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      loadData();
    }, [dataFila]),
  );

  if (loading) {
    return <Loader message="Carregando fila..." />;
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Fila de Espera</Text>
        <Text style={styles.subtitle}>
          {new Date(`${dataFila}T12:00:00`).toLocaleDateString('pt-BR', {
            weekday: 'long',
            day: '2-digit',
            month: 'long',
          })}
        </Text>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{fila.length} na fila</Text>
        </View>
      </View>

      <FlatList
        data={fila}
        keyExtractor={(item) => item.id.toString()}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadData(); }} />
        }
        renderItem={({ item }) => (
          <View style={styles.filaCard}>
            <View style={styles.posicaoBadge}>
              <Text style={styles.posicaoTexto}>{item.posicao}º</Text>
            </View>
            <View style={styles.filaInfo}>
              <Text style={styles.filaNome}>{item.cliente_nome}</Text>
              <Text style={styles.filaDetalhe}>
                {item.tranca_nome} — {item.modelo_nome}
              </Text>
              {item.horario_desejado ? (
                <Text style={styles.filaHorario}>Desejado: {item.horario_desejado.slice(0, 5)}</Text>
              ) : null}
              <Text style={styles.filaStatus}>
                {STATUS_LABEL[item.status] ?? item.status}
                {item.mesmo_dia ? ' · URGENTE' : ''}
              </Text>
            </View>
          </View>
        )}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyTitle}>Fila vazia</Text>
            <Text style={styles.emptyText}>
              Sem horário disponível? Escolha um modelo no catálogo e entre na fila de espera.
            </Text>
            <ButtonPrimary
              title="Ver catálogo"
              onPress={() => router.push('/(tabs)/catalogo')}
            />
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5' },
  header: { backgroundColor: '#7B2CBF', padding: 20, paddingTop: 16 },
  title: { fontSize: 24, fontWeight: '700', color: '#FFF' },
  subtitle: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.85)',
    marginTop: 4,
    textTransform: 'capitalize',
  },
  badge: {
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(255,255,255,0.2)',
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 4,
    marginTop: 12,
  },
  badgeText: { color: '#FFF', fontWeight: '600', fontSize: 13 },
  list: { padding: 16, paddingBottom: 32 },
  filaCard: {
    flexDirection: 'row',
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 10,
    alignItems: 'center',
  },
  posicaoBadge: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#7B2CBF',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 14,
  },
  posicaoTexto: { color: '#FFF', fontSize: 16, fontWeight: '700' },
  filaInfo: { flex: 1 },
  filaNome: { fontSize: 16, fontWeight: '700', color: '#333' },
  filaDetalhe: { fontSize: 14, color: '#7B2CBF', marginTop: 2 },
  filaHorario: { fontSize: 13, color: '#666', marginTop: 4 },
  filaStatus: { fontSize: 12, color: '#999', marginTop: 4, fontWeight: '600' },
  empty: { padding: 40, alignItems: 'center', gap: 16 },
  emptyTitle: { fontSize: 18, fontWeight: '600', color: '#333' },
  emptyText: { fontSize: 14, color: '#999', textAlign: 'center', lineHeight: 22 },
});
