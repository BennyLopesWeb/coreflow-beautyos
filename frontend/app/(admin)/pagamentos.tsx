import React, { useCallback, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  RefreshControl,
  Linking,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { useFocusEffect } from 'expo-router';
import { adminService } from '../../src/services/adminService';
import { PagamentoAdmin } from '../../src/types';
import { Loader } from '../../src/components/Loader';

/**
 * Formata data/hora para exibição.
 */
function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Tela admin de listagem e monitoramento de pagamentos.
 */
export default function AdminPagamentosScreen() {
  const [pagamentos, setPagamentos] = useState<PagamentoAdmin[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async () => {
    try {
      const data = await adminService.listarPagamentos();
      setPagamentos(data);
    } catch (error) {
      console.error('Erro ao carregar pagamentos:', error);
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
    return <Loader message="Carregando pagamentos..." />;
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={pagamentos}
        keyExtractor={(item) => String(item.agendamento_id)}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadData(); }} />
        }
        ListEmptyComponent={
          <Text style={styles.empty}>Nenhum pagamento registrado.</Text>
        }
        renderItem={({ item }) => (
          <View style={styles.card}>
            <View style={styles.cardHeader}>
              <Text style={styles.cliente}>{item.cliente_nome}</Text>
              <View style={[styles.badge, item.sinal_pago ? styles.badgePago : styles.badgePendente]}>
                <Text style={styles.badgeText}>
                  {item.sinal_pago ? 'Pago' : 'Pendente'}
                </Text>
              </View>
            </View>
            <Text style={styles.tranca}>{item.tranca_nome}</Text>
            <Text style={styles.valor}>
              Sinal: R$ {parseFloat(item.valor_sinal).toFixed(2).replace('.', ',')}
            </Text>
            <Text style={styles.meta}>
              {formatDateTime(item.data_hora)} · {item.status_agendamento}
            </Text>
            {item.comprovante_url ? (
              <TouchableOpacity onPress={() => Linking.openURL(item.comprovante_url!)}>
                <Text style={styles.comprovanteLink}>Ver comprovante anexado</Text>
              </TouchableOpacity>
            ) : (
              <Text style={styles.semComprovante}>Sem comprovante</Text>
            )}
            {!item.sinal_pago && item.comprovante_url && (
              <TouchableOpacity
                style={styles.btnConfirmar}
                onPress={async () => {
                  try {
                    // R4-F6: rota legado (agendamento_id) removida — responde 410.
                    // Reservas listadas aqui são sempre pré-R3-F2 (legado histórico);
                    // bookings novos (core-only) não aparecem nesta tela (débito
                    // residual — migração da listagem para booking-first fica para
                    // R4-F7, ver docs/sprints/R4-F6.md).
                    await adminService.confirmarSinal(item.agendamento_id);
                    loadData();
                  } catch (error) {
                    Alert.alert(
                      'Confirmação indisponível',
                      'A confirmação de sinal para reservas legado foi descontinuada (R4-F6). ' +
                        'Reservas novas usam o fluxo booking-first.',
                    );
                  }
                }}
              >
                <Text style={styles.btnConfirmarText}>Confirmar sinal recebido</Text>
              </TouchableOpacity>
            )}
            {item.sinal_pago && item.status_agendamento === 'pending_approval' && (
              <TouchableOpacity
                style={styles.btnAprovar}
                onPress={async () => {
                  await adminService.aprovarReserva(item.agendamento_id);
                  loadData();
                }}
              >
                <Text style={styles.btnAprovarText}>Aprovar reserva</Text>
              </TouchableOpacity>
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
    borderLeftWidth: 4,
    borderLeftColor: '#7B2CBF',
  },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  cliente: { fontSize: 16, fontWeight: '600', color: '#333' },
  tranca: { fontSize: 14, color: '#666', marginTop: 4 },
  valor: { fontSize: 15, fontWeight: '600', color: '#2ECC71', marginTop: 8 },
  meta: { fontSize: 12, color: '#999', marginTop: 4 },
  comprovanteLink: {
    fontSize: 13,
    color: '#7B2CBF',
    fontWeight: '600',
    marginTop: 8,
    textDecorationLine: 'underline',
  },
  semComprovante: { fontSize: 12, color: '#BBB', marginTop: 8, fontStyle: 'italic' },
  badge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  badgePago: { backgroundColor: '#D5F5E3' },
  badgePendente: { backgroundColor: '#FADBD8' },
  badgeText: { fontSize: 12, fontWeight: '600', color: '#333' },
  btnConfirmar: {
    marginTop: 10,
    backgroundColor: '#F39C12',
    padding: 10,
    borderRadius: 8,
    alignItems: 'center',
  },
  btnConfirmarText: { color: '#FFF', fontWeight: '700', fontSize: 13 },
  btnAprovar: {
    marginTop: 10,
    backgroundColor: '#2ECC71',
    padding: 10,
    borderRadius: 8,
    alignItems: 'center',
  },
  btnAprovarText: { color: '#FFF', fontWeight: '700', fontSize: 13 },
});
