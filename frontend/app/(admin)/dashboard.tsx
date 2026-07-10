import React, { useCallback, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  Linking,
  Platform,
  Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../src/contexts/AuthContext';
import { useAdminOperacionalContext } from '../../src/contexts/AdminOperacionalContext';
import { adminService } from '../../src/services/adminService';
import { reservationService, Reservation } from '../../src/services/reservationService';
import { paymentReservationService } from '../../src/services/queueService';
import { AdminDashboard, FilaItem } from '../../src/types';
import { Loader } from '../../src/components/Loader';
import { showAlert } from '../../src/utils/alert';
import { getApiErrorMessage } from '../../src/utils/apiError';

const STATUS_RESERVA: Record<string, string> = {
  pending_payment: 'Aguardando pagamento',
  pending_approval: 'Aguardando aprovação',
  waiting_time_confirmation: 'Ajuste de horário',
};

/**
 * Card de métrica no dashboard admin.
 */
function MetricCard({
  label,
  value,
  icon,
  color,
  onPress,
}: {
  label: string;
  value: string | number;
  icon: keyof typeof Ionicons.glyphMap;
  color: string;
  onPress?: () => void;
}) {
  const content = (
    <View style={[styles.metricCard, { borderTopColor: color }]}>
      <Ionicons name={icon} size={22} color={color} />
      <Text style={styles.metricValue}>{value}</Text>
      <Text style={styles.metricLabel}>{label}</Text>
    </View>
  );
  if (onPress) {
    return <TouchableOpacity onPress={onPress} activeOpacity={0.8}>{content}</TouchableOpacity>;
  }
  return content;
}

/**
 * Dashboard administrativo com fila de reservas e fila de espera em tempo real.
 */
export default function AdminDashboardScreen() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const {
    reservas,
    fila,
    totalPendencias,
    refresh: refreshOperacional,
  } = useAdminOperacionalContext();
  const [data, setData] = useState<AdminDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadAll = async () => {
    try {
      const dashboard = await adminService.obterDashboard();
      setData(dashboard);
      await refreshOperacional();
    } catch (error) {
      console.error('Erro ao carregar dashboard:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      loadAll();
    }, []),
  );

  const actReserva = async (fn: () => Promise<unknown>) => {
    try {
      await fn();
      await loadAll();
    } catch (e: unknown) {
      showAlert('Erro', getApiErrorMessage(e, 'Não foi possível concluir a ação'));
    }
  };

  const actFila = async (id: number, fn: () => Promise<unknown>) => {
    try {
      await fn();
      await loadAll();
    } catch (e: unknown) {
      showAlert('Erro', getApiErrorMessage(e, 'Erro na fila'));
    }
  };

  const aprovarFilaComHorario = (item: FilaItem) => {
    const sugerido = item.horario_desejado ?? '14:00';
    if (Platform.OS === 'web') {
      const hora = window.prompt(`Horário para ${item.cliente_nome} (HH:MM):`, sugerido.slice(0, 5));
      if (!hora) return;
      const [h, m] = hora.split(':');
      const dt = new Date(`${item.data}T00:00:00`);
      dt.setHours(Number(h), Number(m), 0, 0);
      actFila(item.id, () => adminService.aprovarFila(item.id, dt.toISOString()));
      return;
    }
    Alert.prompt(
      'Definir horário',
      `Horário para ${item.cliente_nome}`,
      (text) => {
        if (!text) return;
        const [h, m] = text.split(':');
        const dt = new Date(`${item.data}T00:00:00`);
        dt.setHours(Number(h), Number(m), 0, 0);
        actFila(item.id, () => adminService.aprovarFila(item.id, dt.toISOString()));
      },
      'plain-text',
      sugerido.slice(0, 5),
    );
  };

  if (loading || !data) {
    return <Loader message="Carregando painel..." />;
  }

  const formatMoney = (v: string) =>
    `R$ ${parseFloat(v).toFixed(2).replace('.', ',')}`;

  const renderReserva = (item: Reservation) => (
    <View key={item.id} style={styles.opCard}>
      <View style={styles.opHeader}>
        <Text style={styles.opCliente}>{item.cliente_nome}</Text>
        <Text style={styles.opBadge}>{STATUS_RESERVA[item.status] ?? item.status}</Text>
      </View>
      <Text style={styles.opDetalhe}>
        {item.tranca_nome} — {item.modelo_nome}
      </Text>
      <Text style={styles.opMeta}>
        {new Date(item.data_hora).toLocaleString('pt-BR')} · Sinal R${' '}
        {parseFloat(item.valor_sinal).toFixed(2)}
      </Text>
      {item.sinal_pago ? (
        <Text style={styles.opPago}>Sinal pago — aprovar ou sugerir horário</Text>
      ) : item.comprovante_url ? (
        <TouchableOpacity onPress={() => Linking.openURL(item.comprovante_url!)}>
          <Text style={styles.opLink}>Ver comprovante</Text>
        </TouchableOpacity>
      ) : null}
      <View style={styles.opAcoes}>
        {(item.status === 'pending_payment') && item.comprovante_url && (
          <TouchableOpacity
            style={styles.btnWarn}
            onPress={() => actReserva(() => paymentReservationService.confirmarDeposito(item.id))}
          >
            <Text style={styles.btnText}>Confirmar sinal</Text>
          </TouchableOpacity>
        )}
        {(item.status === 'pending_approval' || item.status === 'waiting_time_confirmation') && (
          <TouchableOpacity
            style={styles.btnOk}
            onPress={() => actReserva(() => reservationService.aprovar(item.id))}
          >
            <Text style={styles.btnText}>Aprovar</Text>
          </TouchableOpacity>
        )}
        <TouchableOpacity
          style={styles.btnAlt}
          onPress={() => router.push('/(admin)/reservas')}
        >
          <Text style={styles.btnText}>Gerenciar</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  const renderFila = (item: FilaItem) => (
    <View key={item.id} style={styles.opCard}>
      <View style={styles.opHeader}>
        <Text style={styles.opCliente}>
          {item.posicao}º — {item.cliente_nome}
          {item.mesmo_dia ? ' · URGENTE' : ''}
        </Text>
      </View>
      <Text style={styles.opDetalhe}>
        {item.tranca_nome} — {item.modelo_nome}
      </Text>
      {item.horario_desejado ? (
        <Text style={styles.opMeta}>Desejado: {item.horario_desejado.slice(0, 5)}</Text>
      ) : null}
      <View style={styles.opAcoes}>
        {item.status === 'waiting' && (
          <TouchableOpacity
            style={styles.btnSec}
            onPress={() => actFila(item.id, () => adminService.contactarFila(item.id))}
          >
            <Text style={styles.btnSecText}>Contactar</Text>
          </TouchableOpacity>
        )}
        <TouchableOpacity style={styles.btnOk} onPress={() => aprovarFilaComHorario(item)}>
          <Text style={styles.btnText}>Aprovar</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => {
            setRefreshing(true);
            loadAll();
          }}
        />
      }
    >
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>Admin — {user?.nome}</Text>
          <Text style={styles.subtitle}>
            {totalPendencias > 0
              ? `${totalPendencias} pendência(s) para revisar`
              : 'Nenhuma pendência no momento'}
          </Text>
        </View>
        <TouchableOpacity onPress={logout} style={styles.logoutBtn}>
          <Ionicons name="log-out-outline" size={22} color="#FFF" />
        </TouchableOpacity>
      </View>

      {totalPendencias > 0 && (
        <View style={styles.alertaBox}>
          <Ionicons name="notifications" size={20} color="#7B2CBF" />
          <Text style={styles.alertaTexto}>
            Há clientes aguardando sua resposta — reservas e fila abaixo.
          </Text>
        </View>
      )}

      <View style={styles.sectionHead}>
        <Text style={styles.sectionTitle}>Reservas para aprovar</Text>
        <TouchableOpacity onPress={() => router.push('/(admin)/reservas')}>
          <Text style={styles.verTudo}>Ver todas ({reservas.length})</Text>
        </TouchableOpacity>
      </View>
      {reservas.length === 0 ? (
        <Text style={styles.emptySection}>Nenhuma reserva pendente.</Text>
      ) : (
        reservas.slice(0, 5).map(renderReserva)
      )}

      <View style={styles.sectionHead}>
        <Text style={styles.sectionTitle}>Fila de espera (hoje)</Text>
        <TouchableOpacity onPress={() => router.push('/(admin)/fila')}>
          <Text style={styles.verTudo}>Ver fila ({fila.length})</Text>
        </TouchableOpacity>
      </View>
      {fila.length === 0 ? (
        <Text style={styles.emptySection}>Ninguém na fila hoje.</Text>
      ) : (
        fila.slice(0, 5).map(renderFila)
      )}

      <Text style={styles.sectionTitle}>Financeiro (mês)</Text>
      <View style={styles.metricsRow}>
        <MetricCard label="Receita" value={formatMoney(data.receita_mes)} icon="trending-up" color="#2ECC71" />
        <MetricCard label="Saldo" value={formatMoney(data.saldo_mes)} icon="wallet" color="#3498DB" />
      </View>

      <Text style={styles.sectionTitle}>Operação</Text>
      <View style={styles.metricsRow}>
        <MetricCard
          label="Reservas pendentes"
          value={data.agendamentos_pendentes}
          icon="bookmark"
          color="#7B2CBF"
          onPress={() => router.push('/(admin)/reservas')}
        />
        <MetricCard
          label="Aguardando aprovação"
          value={data.aguardando_aprovacao ?? 0}
          icon="checkmark-circle"
          color="#E67E22"
          onPress={() => router.push('/(admin)/reservas')}
        />
      </View>
      <View style={styles.metricsRow}>
        <MetricCard label="Agenda hoje" value={data.agendamentos_hoje} icon="calendar" color="#9B59B6" />
        <MetricCard
          label="Na fila"
          value={data.fila_hoje}
          icon="people"
          color="#E74C3C"
          onPress={() => router.push('/(admin)/fila')}
        />
      </View>

      <View style={{ height: 32 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5' },
  header: {
    backgroundColor: '#7B2CBF',
    padding: 24,
    paddingTop: 48,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  greeting: { fontSize: 22, fontWeight: '700', color: '#FFF' },
  subtitle: { fontSize: 14, color: '#E0D0F0', marginTop: 4 },
  logoutBtn: { padding: 8 },
  alertaBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: '#F3E8FF',
    margin: 16,
    marginBottom: 0,
    padding: 14,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#D4BBF0',
  },
  alertaTexto: { flex: 1, color: '#5A2D82', fontSize: 14, fontWeight: '600' },
  sectionHead: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginHorizontal: 16,
    marginTop: 20,
    marginBottom: 8,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginHorizontal: 16,
    marginTop: 20,
    marginBottom: 8,
  },
  verTudo: { color: '#7B2CBF', fontWeight: '700', fontSize: 13 },
  emptySection: {
    textAlign: 'center',
    color: '#999',
    marginHorizontal: 16,
    marginBottom: 8,
    fontSize: 14,
  },
  opCard: {
    backgroundColor: '#FFF',
    marginHorizontal: 16,
    marginBottom: 10,
    padding: 14,
    borderRadius: 10,
    borderLeftWidth: 4,
    borderLeftColor: '#7B2CBF',
  },
  opHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 },
  opCliente: { fontSize: 15, fontWeight: '700', flex: 1 },
  opBadge: { fontSize: 11, color: '#7B2CBF', fontWeight: '700' },
  opDetalhe: { color: '#666', marginTop: 4, fontSize: 14 },
  opMeta: { color: '#888', marginTop: 4, fontSize: 12 },
  opPago: { color: '#2ECC71', fontWeight: '600', fontSize: 12, marginTop: 4 },
  opLink: { color: '#7B2CBF', fontWeight: '600', marginTop: 4, fontSize: 13 },
  opAcoes: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 10 },
  btnOk: { backgroundColor: '#2ECC71', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 6 },
  btnWarn: { backgroundColor: '#F39C12', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 6 },
  btnAlt: { backgroundColor: '#3498DB', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 6 },
  btnSec: {
    borderWidth: 1,
    borderColor: '#7B2CBF',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
  },
  btnSecText: { color: '#7B2CBF', fontSize: 12, fontWeight: '700' },
  btnText: { color: '#FFF', fontSize: 12, fontWeight: '700' },
  metricsRow: { flexDirection: 'row', paddingHorizontal: 12, gap: 8 },
  metricCard: {
    flex: 1,
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    borderTopWidth: 3,
    marginHorizontal: 4,
    elevation: 2,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 4,
  },
  metricValue: { fontSize: 20, fontWeight: '700', color: '#333', marginTop: 8 },
  metricLabel: { fontSize: 12, color: '#888', marginTop: 2 },
});
