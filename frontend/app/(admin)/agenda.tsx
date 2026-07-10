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
import { AgendamentoAdmin, StatusAgendamento } from '../../src/types';
import { Loader } from '../../src/components/Loader';
import { getApiErrorMessage } from '../../src/utils/apiError';

/**
 * Exibe alerta compatível web/mobile.
 */
function showAlert(title: string, message: string) {
  if (Platform.OS === 'web') {
    window.alert(`${title}\n\n${message}`);
    return;
  }
  Alert.alert(title, message);
}

/**
 * Formata data/hora para exibição.
 */
function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

const STATUS_OPCOES: StatusAgendamento[] = ['pendente', 'confirmado', 'concluido', 'cancelado'];

/**
 * Tela admin de gestão da agenda.
 */
export default function AdminAgendaScreen() {
  const [agendamentos, setAgendamentos] = useState<AgendamentoAdmin[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const hoje = new Date().toISOString().split('T')[0];

  const loadData = async () => {
    try {
      const data = await adminService.listarAgenda(hoje);
      setAgendamentos(data);
    } catch (error) {
      console.error('Erro ao carregar agenda:', error);
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

  /**
   * Atualiza status de um agendamento.
   */
  const alterarStatus = async (id: number, status: StatusAgendamento) => {
    try {
      await adminService.atualizarStatusAgenda(id, status);
      showAlert('Sucesso', `Status alterado para ${status}`);
      loadData();
    } catch (error) {
      showAlert('Erro', getApiErrorMessage(error, 'Falha ao atualizar'));
    }
  };

  if (loading) {
    return <Loader message="Carregando agenda..." />;
  }

  return (
    <View style={styles.container}>
      <Text style={styles.dateLabel}>Agenda de hoje ({hoje})</Text>
      <FlatList
        data={agendamentos}
        keyExtractor={(item) => String(item.id)}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadData(); }} />
        }
        ListEmptyComponent={
          <Text style={styles.empty}>Nenhum agendamento para hoje.</Text>
        }
        renderItem={({ item }) => (
          <View style={styles.card}>
            <Text style={styles.horario}>{formatDateTime(item.data_hora)}</Text>
            <Text style={styles.cliente}>{item.cliente_nome}</Text>
            <Text style={styles.tranca}>
              {item.tranca_nome}
              {item.imagem_label ? ` · ${item.imagem_label}` : ''}
            </Text>
            <Text style={styles.meta}>
              {item.sinal_pago ? '✓ Sinal pago' : '⏳ Aguardando sinal'}
              {item.na_fila ? ` · Fila #${item.posicao_fila}` : ''}
            </Text>
            <View style={styles.statusRow}>
              {STATUS_OPCOES.map((s) => (
                <TouchableOpacity
                  key={s}
                  style={[styles.statusBtn, item.status === s && styles.statusBtnActive]}
                  onPress={() => alterarStatus(item.id, s)}
                >
                  <Text style={[styles.statusText, item.status === s && styles.statusTextActive]}>
                    {s}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5' },
  dateLabel: { padding: 16, fontSize: 14, color: '#666', fontWeight: '600' },
  empty: { textAlign: 'center', color: '#888', marginTop: 40 },
  card: {
    backgroundColor: '#FFF',
    marginHorizontal: 16,
    marginBottom: 8,
    padding: 16,
    borderRadius: 10,
  },
  horario: { fontSize: 18, fontWeight: '700', color: '#7B2CBF' },
  cliente: { fontSize: 16, fontWeight: '600', marginTop: 4 },
  tranca: { fontSize: 14, color: '#666' },
  meta: { fontSize: 13, color: '#888', marginTop: 6 },
  statusRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 12 },
  statusBtn: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: '#EEE',
  },
  statusBtnActive: { backgroundColor: '#7B2CBF' },
  statusText: { fontSize: 11, color: '#555', textTransform: 'capitalize' },
  statusTextActive: { color: '#FFF', fontWeight: '600' },
});
