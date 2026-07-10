import React, { useCallback, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  RefreshControl,
  TouchableOpacity,
  Alert,
  Platform,
} from 'react-native';
import { useFocusEffect } from 'expo-router';
import { adminService } from '../../src/services/adminService';
import { FilaItem, StatusFila } from '../../src/types';
import { useAdminOperacionalContext } from '../../src/contexts/AdminOperacionalContext';
import { Loader } from '../../src/components/Loader';

const STATUS_LABEL: Record<StatusFila, string> = {
  waiting: 'Aguardando',
  contacted: 'Contactado',
  approved: 'Aprovado',
  rejected: 'Rejeitado',
  cancelled: 'Cancelado',
};

/**
 * Tela admin de gestão da fila de espera (FIFO).
 */
export default function AdminFilaScreen() {
  const { refresh: refreshOperacional } = useAdminOperacionalContext();
  const [fila, setFila] = useState<FilaItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [acaoId, setAcaoId] = useState<number | null>(null);

  const hoje = new Date().toISOString().split('T')[0];

  const loadData = async () => {
    try {
      const data = await adminService.consultarFila(hoje);
      setFila(data.posicoes);
      setTotal(data.total_pessoas);
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
    }, []),
  );

  const executar = async (id: number, fn: () => Promise<unknown>) => {
    setAcaoId(id);
    try {
      await fn();
      await loadData();
      await refreshOperacional();
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : 'Erro na operação';
      if (Platform.OS === 'web') window.alert(msg);
      else Alert.alert('Erro', msg);
    } finally {
      setAcaoId(null);
    }
  };

  const aprovarComHorario = (item: FilaItem) => {
    const sugerido = item.horario_desejado ?? '14:00';
    if (Platform.OS === 'web') {
      const hora = window.prompt(
        `Horário para ${item.cliente_nome} (HH:MM):`,
        sugerido.slice(0, 5),
      );
      if (!hora) return;
      const [h, m] = hora.split(':');
      const dt = new Date();
      dt.setHours(Number(h), Number(m), 0, 0);
      executar(item.id, () => adminService.aprovarFila(item.id, dt.toISOString()));
      return;
    }
    Alert.prompt(
      'Definir horário',
      `Horário para ${item.cliente_nome}`,
      (text) => {
        if (!text) return;
        const [h, m] = text.split(':');
        const dt = new Date();
        dt.setHours(Number(h), Number(m), 0, 0);
        executar(item.id, () => adminService.aprovarFila(item.id, dt.toISOString()));
      },
      'plain-text',
      sugerido.slice(0, 5),
    );
  };

  if (loading) {
    return <Loader message="Carregando fila..." />;
  }

  return (
    <View style={styles.container}>
      <View style={styles.summary}>
        <Text style={styles.summaryTitle}>Fila de hoje</Text>
        <Text style={styles.summaryCount}>{total} pessoa(s)</Text>
      </View>
      <FlatList
        data={fila}
        keyExtractor={(item) => String(item.id)}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadData(); }} />
        }
        ListEmptyComponent={
          <Text style={styles.empty}>Ninguém na fila hoje.</Text>
        }
        renderItem={({ item }) => (
          <View style={styles.card}>
            <View style={styles.posicao}>
              <Text style={styles.posicaoNum}>{item.posicao}</Text>
            </View>
            <View style={styles.info}>
              <Text style={styles.cliente}>
                {item.cliente_nome}
                {item.mesmo_dia ? ' · URGENTE' : ''}
              </Text>
              <Text style={styles.tranca}>{item.tranca_nome} — {item.modelo_nome}</Text>
              {item.horario_desejado ? (
                <Text style={styles.horario}>Desejado: {item.horario_desejado.slice(0, 5)}</Text>
              ) : null}
              <Text style={styles.status}>{STATUS_LABEL[item.status] ?? item.status}</Text>
              {item.observacoes ? (
                <Text style={styles.obs}>{item.observacoes}</Text>
              ) : null}
              {(item.status === 'waiting' || item.status === 'contacted') && (
                <View style={styles.acoes}>
                  {item.status === 'waiting' && (
                    <TouchableOpacity
                      style={styles.btnSec}
                      disabled={acaoId === item.id}
                      onPress={() => executar(item.id, () => adminService.contactarFila(item.id))}
                    >
                      <Text style={styles.btnSecText}>Contactar</Text>
                    </TouchableOpacity>
                  )}
                  <TouchableOpacity
                    style={styles.btnPrim}
                    disabled={acaoId === item.id}
                    onPress={() => aprovarComHorario(item)}
                  >
                    <Text style={styles.btnPrimText}>Aprovar</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={styles.btnRej}
                    disabled={acaoId === item.id}
                    onPress={() => executar(item.id, () => adminService.rejeitarFila(item.id))}
                  >
                    <Text style={styles.btnRejText}>Rejeitar</Text>
                  </TouchableOpacity>
                </View>
              )}
            </View>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5' },
  summary: {
    backgroundColor: '#7B2CBF',
    padding: 20,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  summaryTitle: { color: '#FFF', fontSize: 16 },
  summaryCount: { color: '#FFF', fontSize: 24, fontWeight: '700' },
  empty: { textAlign: 'center', color: '#888', marginTop: 40 },
  card: {
    flexDirection: 'row',
    backgroundColor: '#FFF',
    marginHorizontal: 16,
    marginVertical: 6,
    padding: 16,
    borderRadius: 10,
    alignItems: 'flex-start',
  },
  posicao: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#7B2CBF',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 14,
  },
  posicaoNum: { color: '#FFF', fontSize: 18, fontWeight: '700' },
  info: { flex: 1 },
  cliente: { fontSize: 16, fontWeight: '600' },
  tranca: { fontSize: 14, color: '#666', marginTop: 2 },
  horario: { fontSize: 12, color: '#999', marginTop: 4 },
  status: { fontSize: 12, color: '#7B2CBF', fontWeight: '600', marginTop: 4 },
  obs: { fontSize: 12, color: '#888', marginTop: 4, fontStyle: 'italic' },
  acoes: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 10 },
  btnPrim: {
    backgroundColor: '#7B2CBF',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
  },
  btnPrimText: { color: '#FFF', fontSize: 12, fontWeight: '700' },
  btnSec: {
    borderWidth: 1,
    borderColor: '#7B2CBF',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
  },
  btnSecText: { color: '#7B2CBF', fontSize: 12, fontWeight: '700' },
  btnRej: {
    borderWidth: 1,
    borderColor: '#DC3545',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
  },
  btnRejText: { color: '#DC3545', fontSize: 12, fontWeight: '700' },
});
