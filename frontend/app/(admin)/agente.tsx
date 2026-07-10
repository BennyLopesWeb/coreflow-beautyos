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
import { agenteService } from '../../src/services/agenteService';
import { AgentTask } from '../../src/types';
import { Loader } from '../../src/components/Loader';
import { ButtonPrimary } from '../../src/components/ButtonPrimary';
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
 * Tela do agente inteligente — automação de tarefas CRM/atendimento.
 */
export default function AdminAgenteScreen() {
  const [tarefas, setTarefas] = useState<AgentTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [executando, setExecutando] = useState(false);

  const loadData = async () => {
    try {
      const data = await agenteService.listarTarefas();
      setTarefas(data);
    } catch (error) {
      console.error('Erro ao carregar tarefas:', error);
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
   * Executa ciclo completo do agente (análise + automação).
   */
  const executarAgente = async () => {
    setExecutando(true);
    try {
      const result = await agenteService.executarAutomacoes();
      setTarefas(result.tarefas);
      showAlert('Agente IA', result.mensagem);
    } catch (error) {
      showAlert('Erro', getApiErrorMessage(error, 'Falha ao executar agente'));
    } finally {
      setExecutando(false);
    }
  };

  /**
   * Executa uma tarefa pendente manualmente.
   */
  const executarTarefa = async (taskId: number) => {
    try {
      await agenteService.executarTarefa(taskId);
      loadData();
      showAlert('Sucesso', 'Tarefa executada');
    } catch (error) {
      showAlert('Erro', getApiErrorMessage(error, 'Falha ao executar tarefa'));
    }
  };

  if (loading) {
    return <Loader message="Carregando agente..." />;
  }

  return (
    <View style={styles.container}>
      <View style={styles.hero}>
        <Text style={styles.heroTitle}>Agente Inteligente</Text>
        <Text style={styles.heroDesc}>
          Analisa pagamentos pendentes, clientes inativos e fila do dia.
          Cria e executa tarefas automatizadas de CRM e atendimento.
        </Text>
        <ButtonPrimary
          title="Executar automações"
          onPress={executarAgente}
          loading={executando}
        />
      </View>

      <FlatList
        data={tarefas}
        keyExtractor={(item) => String(item.id)}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadData(); }} />
        }
        ListEmptyComponent={
          <Text style={styles.empty}>
            Nenhuma tarefa. Toque em &quot;Executar automações&quot; para analisar o salão.
          </Text>
        }
        renderItem={({ item }) => (
          <View style={styles.card}>
            <View style={styles.cardHeader}>
              <Text style={styles.titulo}>{item.titulo}</Text>
              <View style={[
                styles.badge,
                item.status === 'executada' ? styles.badgeOk : styles.badgePend,
              ]}>
                <Text style={styles.badgeText}>{item.status}</Text>
              </View>
            </View>
            <Text style={styles.descricao}>{item.descricao}</Text>
            {item.resultado && (
              <Text style={styles.resultado}>✓ {item.resultado}</Text>
            )}
            {item.status === 'pendente' && (
              <TouchableOpacity
                style={styles.execBtn}
                onPress={() => executarTarefa(item.id)}
              >
                <Text style={styles.execBtnText}>Executar agora</Text>
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
  hero: {
    backgroundColor: '#7B2CBF',
    padding: 20,
    marginBottom: 8,
  },
  heroTitle: { color: '#FFF', fontSize: 20, fontWeight: '700' },
  heroDesc: { color: '#E0D0F0', fontSize: 14, marginVertical: 12, lineHeight: 20 },
  empty: { textAlign: 'center', color: '#888', margin: 24, lineHeight: 22 },
  card: {
    backgroundColor: '#FFF',
    marginHorizontal: 16,
    marginVertical: 6,
    padding: 16,
    borderRadius: 10,
  },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  titulo: { fontSize: 15, fontWeight: '600', flex: 1, marginRight: 8 },
  descricao: { fontSize: 13, color: '#666', marginTop: 8, lineHeight: 18 },
  resultado: { fontSize: 12, color: '#27AE60', marginTop: 8 },
  badge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 10 },
  badgeOk: { backgroundColor: '#D5F5E3' },
  badgePend: { backgroundColor: '#FDEBD0' },
  badgeText: { fontSize: 11, fontWeight: '600', textTransform: 'capitalize' },
  execBtn: {
    marginTop: 12,
    alignSelf: 'flex-start',
    backgroundColor: '#7B2CBF',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
  },
  execBtnText: { color: '#FFF', fontSize: 13, fontWeight: '600' },
});
