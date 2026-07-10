import React, { useCallback, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  RefreshControl,
  Alert,
  Platform,
} from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { agendamentoService } from '../../src/services/agendamentoService';
import { Agendamento } from '../../src/types';
import { Loader } from '../../src/components/Loader';
import { ButtonPrimary } from '../../src/components/ButtonPrimary';
import { getApiErrorMessage } from '../../src/utils/apiError';

/**
 * Exibe alerta compatível com web e mobile.
 */
function showAlert(title: string, message: string, onOk?: () => void) {
  if (Platform.OS === 'web') {
    window.alert(`${title}\n\n${message}`);
    onOk?.();
    return;
  }
  Alert.alert(title, message, [{ text: 'OK', onPress: onOk }]);
}

/**
 * Lista agendamentos do cliente.
 */
export default function AgendamentosScreen() {
  const router = useRouter();
  const [agendamentos, setAgendamentos] = useState<Agendamento[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const STATUS_LABEL: Record<string, string> = {
    pendente: 'Aguardando pagamento',
    pending_approval: 'Aguardando aprovação',
    confirmado: 'Confirmado',
    cancelado: 'Cancelado',
    concluido: 'Concluído',
    no_show: 'Não compareceu',
  };

  const loadAgendamentos = async () => {
    try {
      const data = await agendamentoService.listar();
      setAgendamentos(data);
    } catch (error) {
      console.error('Erro ao carregar agendamentos:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      loadAgendamentos();
    }, [])
  );

  const handleRefresh = () => {
    setRefreshing(true);
    loadAgendamentos();
  };

  if (loading) {
    return <Loader message="Carregando agendamentos..." />;
  }

  return (
    <View style={styles.container}>
      <View style={styles.headerBar}>
        <Text style={styles.title}>Agendamentos</Text>
        <ButtonPrimary
          title="+ Novo"
          onPress={() => router.push('/(tabs)/catalogo')}
        />
      </View>
      <FlatList
        data={agendamentos}
        keyExtractor={(item) => item.id.toString()}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>
              Agendamento #{item.id}
            </Text>
            <Text style={styles.cardText}>
              {new Date(item.data_hora).toLocaleString('pt-BR')}
            </Text>
            <View style={styles.statusContainer}>
              <Text style={[styles.status, styles[`status${item.status}` as keyof typeof styles]]}>
                {STATUS_LABEL[item.status] ?? item.status}
              </Text>
              {item.sinal_pago && (
                <Text style={styles.sinalPago}>✓ Sinal pago</Text>
              )}
            </View>
          </View>
        )}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyTitle}>Nenhum agendamento</Text>
            <Text style={styles.emptyText}>
              Vá ao catálogo e agende um serviço para começar.
            </Text>
            <ButtonPrimary
              title="Agendar Agora"
              onPress={() => router.push('/(tabs)/catalogo')}
            />
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  headerBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#FFF',
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: '#333',
  },
  list: {
    padding: 16,
    paddingBottom: 32,
  },
  card: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#333',
    marginBottom: 8,
  },
  cardText: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  statusContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    alignItems: 'center',
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#F0F0F0',
  },
  status: {
    fontSize: 12,
    fontWeight: '600',
    textTransform: 'uppercase',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  statuspendente: {
    backgroundColor: '#FFF3CD',
    color: '#856404',
  },
  statuspending_approval: {
    backgroundColor: '#E8DAEF',
    color: '#6C3483',
  },
  statusconfirmado: {
    backgroundColor: '#D4EDDA',
    color: '#155724',
  },
  statuscancelado: {
    backgroundColor: '#F8D7DA',
    color: '#721C24',
  },
  statusconcluido: {
    backgroundColor: '#D1ECF1',
    color: '#0C5460',
  },
  sinalPago: {
    fontSize: 12,
    color: '#28A745',
    fontWeight: '600',
  },
  naFila: {
    fontSize: 12,
    color: '#E67E22',
    fontWeight: '600',
  },
  actionRow: {
    marginTop: 12,
  },
  empty: {
    padding: 40,
    alignItems: 'center',
    gap: 12,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
  },
  emptyText: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
    marginBottom: 8,
  },
});
