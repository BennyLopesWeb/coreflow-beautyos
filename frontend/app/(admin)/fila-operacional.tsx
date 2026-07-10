import React, { useCallback, useState } from 'react';
import {
  View, Text, StyleSheet, FlatList, RefreshControl, TouchableOpacity, Alert, Platform,
} from 'react-native';
import { useFocusEffect } from 'expo-router';
import { queueService, QueueEntry } from '../../src/services/queueService';
import { paymentReservationService } from '../../src/services/queueService';
import { Loader } from '../../src/components/Loader';

const STATUS: Record<string, string> = {
  waiting: 'Aguardando',
  called: 'Chamado',
  checked_in: 'Check-in',
  in_service: 'Em atendimento',
  completed: 'Concluído',
  cancelled: 'Cancelado',
};

/**
 * Painel admin da fila operacional do dia.
 */
export default function AdminFilaOperacionalScreen() {
  const [entries, setEntries] = useState<QueueEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const hoje = new Date().toISOString().split('T')[0];

  const load = async () => {
    try {
      const data = await queueService.listar(hoje);
      setEntries(data.entries);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(useCallback(() => { load(); }, []));

  const act = async (id: number, fn: () => Promise<unknown>) => {
    try {
      await fn();
      await load();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Erro';
      Platform.OS === 'web' ? window.alert(msg) : Alert.alert('Erro', msg);
    }
  };

  if (loading) return <Loader message="Carregando fila operacional..." />;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Fila de Atendimento</Text>
        <Text style={styles.count}>{entries.length} na fila</Text>
      </View>
      <FlatList
        data={entries}
        keyExtractor={(i) => String(i.id)}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} />}
        ListEmptyComponent={<Text style={styles.empty}>Fila vazia hoje.</Text>}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <Text style={styles.pos}>{item.posicao}º</Text>
            <View style={styles.info}>
              <Text style={styles.nome}>{item.cliente_nome}{item.mesmo_dia ? ' · URGENTE' : ''}</Text>
              <Text style={styles.meta}>{item.tranca_nome} — {item.modelo_nome}</Text>
              <Text style={styles.status}>{STATUS[item.status] ?? item.status}</Text>
              <View style={styles.acoes}>
                {item.status === 'waiting' && (
                  <TouchableOpacity style={styles.btn} onPress={() => act(item.id, () => queueService.chamar(item.id))}>
                    <Text style={styles.btnText}>Chamar</Text>
                  </TouchableOpacity>
                )}
                {item.status === 'called' && (
                  <TouchableOpacity style={styles.btn} onPress={() => act(item.id, () => queueService.checkin(item.id))}>
                    <Text style={styles.btnText}>Check-in</Text>
                  </TouchableOpacity>
                )}
                {item.status === 'checked_in' && (
                  <TouchableOpacity style={styles.btn} onPress={() => act(item.id, () => queueService.iniciar(item.id))}>
                    <Text style={styles.btnText}>Iniciar</Text>
                  </TouchableOpacity>
                )}
                {item.status === 'in_service' && (
                  <TouchableOpacity style={[styles.btn, styles.btnOk]} onPress={() => act(item.id, () => queueService.concluir(item.id))}>
                    <Text style={styles.btnText}>Finalizar</Text>
                  </TouchableOpacity>
                )}
                {item.agendamento_id && item.status === 'in_service' && (
                  <TouchableOpacity
                    style={[styles.btn, styles.btnPay]}
                    onPress={() => act(item.agendamento_id!, () =>
                      paymentReservationService.confirmarFinal(item.agendamento_id!))}
                  >
                    <Text style={styles.btnText}>Pag. Final</Text>
                  </TouchableOpacity>
                )}
              </View>
            </View>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5' },
  header: { backgroundColor: '#2ECC71', padding: 20, flexDirection: 'row', justifyContent: 'space-between' },
  title: { color: '#FFF', fontSize: 18, fontWeight: '700' },
  count: { color: '#FFF', fontSize: 22, fontWeight: '700' },
  empty: { textAlign: 'center', color: '#888', marginTop: 40 },
  card: { flexDirection: 'row', backgroundColor: '#FFF', margin: 8, padding: 14, borderRadius: 10 },
  pos: { fontSize: 22, fontWeight: '800', color: '#2ECC71', width: 40 },
  info: { flex: 1 },
  nome: { fontSize: 16, fontWeight: '700' },
  meta: { color: '#666', marginTop: 2 },
  status: { color: '#2ECC71', fontWeight: '600', marginTop: 4 },
  acoes: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 10 },
  btn: { backgroundColor: '#7B2CBF', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 6 },
  btnOk: { backgroundColor: '#2ECC71' },
  btnPay: { backgroundColor: '#E67E22' },
  btnText: { color: '#FFF', fontWeight: '700', fontSize: 12 },
});
