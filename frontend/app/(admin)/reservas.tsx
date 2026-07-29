import React, { useCallback, useMemo, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  RefreshControl,
  TouchableOpacity,
  Alert,
  Platform,
  Linking,
} from 'react-native';
import { useFocusEffect } from 'expo-router';
import {
  reservationService,
  Reservation,
  lastReservationListMeta,
} from '../../src/services/reservationService';
import { paymentReservationService } from '../../src/services/queueService';
import { useAdminOperacionalContext } from '../../src/contexts/AdminOperacionalContext';
import { Loader } from '../../src/components/Loader';
import { getApiErrorMessage } from '../../src/utils/apiError';
import { showAlert } from '../../src/utils/alert';

const STATUS_LABEL: Record<string, string> = {
  pending_payment: 'Aguardando pagamento',
  pending_approval: 'Aguardando aprovação',
  waiting_time_confirmation: 'Aguardando cliente confirmar horário',
  approved: 'Aprovada',
  rejected: 'Rejeitada',
  in_queue: 'Na fila',
  checked_in: 'Check-in',
  in_service: 'Em atendimento',
  completed: 'Concluída',
  paid: 'Paga',
  cancelled: 'Cancelada',
  pendente: 'Aguardando pagamento',
  confirmado: 'Aprovada',
};

/** Status que exigem ação ou acompanhamento da profissional. */
const STATUS_ACAO = new Set([
  'pending_payment',
  'pending_approval',
  'waiting_time_confirmation',
  'pendente',
]);

type FiltroReserva = 'pendentes' | 'todas';

/**
 * Formata total/sinal da reserva sem exibir ``NaN%`` quando o percentual
 * não for calculável.
 *
 * Args:
 *   item: Reserva mapeada (valores como string).
 *
 * Returns:
 *   Texto monetário; inclui percentual apenas se for um número finito.
 */
function formatValoresReserva(item: Reservation): string {
  const total = Number.parseFloat(item.valor_total);
  const sinal = Number.parseFloat(item.valor_sinal);
  const totalTxt = Number.isFinite(total) ? total.toFixed(2) : '—';
  const sinalTxt = Number.isFinite(sinal) ? sinal.toFixed(2) : '—';
  const pct = Number.parseFloat(item.percentual_sinal);
  if (!Number.isFinite(pct)) {
    return `Total R$ ${totalTxt} · Sinal R$ ${sinalTxt}`;
  }
  return `Total R$ ${totalTxt} · Sinal R$ ${sinalTxt} (${Math.round(pct * 100)}%)`;
}

/**
 * Painel admin de reservas — exibe novas solicitações e as aguardando aprovação.
 */
export default function AdminReservasScreen() {
  const { refresh: refreshOperacional } = useAdminOperacionalContext();
  const [reservas, setReservas] = useState<Reservation[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filtro, setFiltro] = useState<FiltroReserva>('pendentes');
  const [erro, setErro] = useState<string | null>(null);
  /** True quando GET /v1/bookings atingiu o teto interno (pode haver mais). */
  const [listaTruncada, setListaTruncada] = useState(false);

  /**
   * Carrega reservas da API admin (Core + enriquecimento de nome/comprovante).
   */
  const load = async () => {
    try {
      setErro(null);
      const data = await reservationService.listar(
        filtro === 'pendentes' ? { pendentes: true } : undefined,
      );
      setReservas(data);
      setListaTruncada(lastReservationListMeta.truncated);
    } catch (e: unknown) {
      setErro(getApiErrorMessage(e, 'Erro ao carregar reservas'));
      setReservas([]);
      setListaTruncada(false);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      load();
    }, [filtro]),
  );

  const reservasOrdenadas = useMemo(() => {
    const ordem = (s: string) => {
      if (s === 'pending_approval' || s === 'pendente') return 0;
      if (s === 'pending_payment') return 1;
      if (s === 'waiting_time_confirmation') return 2;
      return 3;
    };
    return [...reservas].sort((a, b) => ordem(a.status) - ordem(b.status));
  }, [reservas]);

  /**
   * Executa ação admin e recarrega a lista.
   */
  const act = async (fn: () => Promise<unknown>) => {
    try {
      await fn();
      await load();
      await refreshOperacional();
    } catch (e: unknown) {
      showAlert('Erro', getApiErrorMessage(e, 'Não foi possível concluir a ação'));
    }
  };

  /**
   * Abre prompt para sugerir novo horário à cliente.
   */
  const sugerirHorario = (item: Reservation) => {
    const sugerir = (novoHorario: string, mensagem: string) => {
      if (!novoHorario.trim()) {
        showAlert('Horário obrigatório', 'Informe a data e hora sugeridas (ex: 2026-06-30T14:00:00)');
        return;
      }
      act(() =>
        reservationService.reagendar(item.id, novoHorario.trim(), mensagem.trim() || undefined),
      );
    };

    if (Platform.OS === 'web') {
      const novoHorario = window.prompt(
        'Novo horário sugerido (AAAA-MM-DDTHH:MM:00)',
        item.data_hora.slice(0, 19),
      );
      if (novoHorario === null) return;
      const mensagem = window.prompt('Mensagem para a cliente (opcional)', '') ?? '';
      sugerir(novoHorario, mensagem);
      return;
    }

    Alert.prompt(
      'Sugerir horário',
      'Informe data/hora (AAAA-MM-DDTHH:MM:00)',
      (novoHorario) => {
        if (!novoHorario) return;
        Alert.prompt('Mensagem', 'Opcional', (mensagem) => sugerir(novoHorario, mensagem ?? ''));
      },
      'plain-text',
      item.data_hora.slice(0, 19),
    );
  };

  if (loading) return <Loader message="Carregando reservas..." />;

  return (
    <View style={styles.container}>
      <View style={styles.filtros}>
        <TouchableOpacity
          style={[styles.filtroBtn, filtro === 'pendentes' && styles.filtroAtivo]}
          onPress={() => setFiltro('pendentes')}
        >
          <Text style={[styles.filtroTexto, filtro === 'pendentes' && styles.filtroTextoAtivo]}>
            Pendentes
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.filtroBtn, filtro === 'todas' && styles.filtroAtivo]}
          onPress={() => setFiltro('todas')}
        >
          <Text style={[styles.filtroTexto, filtro === 'todas' && styles.filtroTextoAtivo]}>
            Todas
          </Text>
        </TouchableOpacity>
      </View>

      {erro ? <Text style={styles.erro}>{erro}</Text> : null}

      {listaTruncada ? (
        <Text style={styles.avisoTruncado}>
          A lista pode conter mais de 100 reservas. A paginação ainda não está disponível.
        </Text>
      ) : null}

      <FlatList
        data={reservasOrdenadas}
        keyExtractor={(i) => String(i.id)}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              load();
            }}
          />
        }
        ListEmptyComponent={
          <Text style={styles.empty}>
            {filtro === 'pendentes'
              ? 'Nenhuma reserva pendente no momento.'
              : 'Nenhuma reserva encontrada.'}
          </Text>
        }
        renderItem={({ item }) => (
          <View style={[styles.card, STATUS_ACAO.has(item.status) && styles.cardPendente]}>
            <Text style={styles.cliente}>{item.cliente_nome ?? `Cliente #${item.cliente_id}`}</Text>
            <Text style={styles.modelo}>
              {item.tranca_nome} — {item.modelo_nome ?? 'Modelo'}
            </Text>
            <Text style={styles.meta}>
              Solicitado: {new Date(item.data_hora).toLocaleString('pt-BR')}
            </Text>
            {item.horario_sugerido ? (
              <Text style={styles.sugerido}>
                Horário sugerido: {new Date(item.horario_sugerido).toLocaleString('pt-BR')}
              </Text>
            ) : null}
            <Text style={styles.meta}>
              {formatValoresReserva(item)}
            </Text>
            <Text style={styles.status}>{STATUS_LABEL[item.status] ?? item.status}</Text>
            {item.sinal_pago ? (
              <Text style={styles.pagoOk}>Sinal pago — aguardando sua aprovação</Text>
            ) : item.comprovante_url ? (
              <Text style={styles.comprovanteHint}>Comprovante anexado — confirme o sinal</Text>
            ) : (
              <Text style={styles.aguardandoPag}>Aguardando pagamento do sinal</Text>
            )}

            {item.comprovante_url ? (
              <TouchableOpacity onPress={() => Linking.openURL(item.comprovante_url!)}>
                <Text style={styles.linkComprovante}>Ver comprovante</Text>
              </TouchableOpacity>
            ) : null}

            <View style={styles.acoes}>
              {(item.status === 'pending_payment' || item.status === 'pendente') &&
                item.comprovante_url && (
                  <TouchableOpacity
                    style={styles.btnWarn}
                    onPress={() =>
                      act(() => paymentReservationService.confirmarDeposito(item.id))
                    }
                  >
                    <Text style={styles.btnText}>Confirmar sinal</Text>
                  </TouchableOpacity>
                )}
              {(item.status === 'pending_approval' ||
                item.status === 'waiting_time_confirmation') && (
                <TouchableOpacity
                  style={styles.btnOk}
                  onPress={() => act(() => reservationService.aprovar(item.id))}
                >
                  <Text style={styles.btnText}>Aprovar</Text>
                </TouchableOpacity>
              )}
              {STATUS_ACAO.has(item.status) && (
                <TouchableOpacity style={styles.btnAlt} onPress={() => sugerirHorario(item)}>
                  <Text style={styles.btnText}>Sugerir horário</Text>
                </TouchableOpacity>
              )}
              {STATUS_ACAO.has(item.status) && (
                <TouchableOpacity
                  style={styles.btnRej}
                  onPress={() => act(() => reservationService.rejeitar(item.id, 'Indisponível'))}
                >
                  <Text style={styles.btnText}>Rejeitar</Text>
                </TouchableOpacity>
              )}
              {item.status === 'completed' && (
                <TouchableOpacity
                  style={styles.btnPay}
                  onPress={() => act(() => paymentReservationService.confirmarFinal(item.id))}
                >
                  <Text style={styles.btnText}>Pag. Final</Text>
                </TouchableOpacity>
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
  filtros: { flexDirection: 'row', padding: 12, gap: 8, backgroundColor: '#FFF' },
  filtroBtn: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: '#EEE',
  },
  filtroAtivo: { backgroundColor: '#7B2CBF' },
  filtroTexto: { fontWeight: '600', color: '#666' },
  filtroTextoAtivo: { color: '#FFF' },
  erro: { color: '#DC3545', textAlign: 'center', padding: 12 },
  avisoTruncado: {
    color: '#8A6D3B',
    backgroundColor: '#FCF8E3',
    textAlign: 'center',
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 13,
    lineHeight: 18,
  },
  empty: { textAlign: 'center', color: '#888', marginTop: 40, paddingHorizontal: 24 },
  card: {
    backgroundColor: '#FFF',
    margin: 10,
    padding: 16,
    borderRadius: 10,
    borderLeftWidth: 4,
    borderLeftColor: '#CCC',
  },
  cardPendente: { borderLeftColor: '#7B2CBF' },
  cliente: { fontSize: 16, fontWeight: '700' },
  modelo: { color: '#666', marginTop: 4 },
  meta: { color: '#888', marginTop: 4, fontSize: 13 },
  sugerido: { color: '#E67E22', marginTop: 4, fontSize: 13, fontWeight: '600' },
  status: { marginTop: 8, fontWeight: '700', color: '#333' },
  pagoOk: { marginTop: 4, color: '#2ECC71', fontWeight: '600', fontSize: 13 },
  comprovanteHint: { marginTop: 4, color: '#F39C12', fontWeight: '600', fontSize: 13 },
  aguardandoPag: { marginTop: 4, color: '#888', fontSize: 13 },
  linkComprovante: { color: '#7B2CBF', marginTop: 8, fontWeight: '600' },
  acoes: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 12 },
  btnOk: { backgroundColor: '#2ECC71', padding: 8, borderRadius: 6 },
  btnWarn: { backgroundColor: '#F39C12', padding: 8, borderRadius: 6 },
  btnAlt: { backgroundColor: '#3498DB', padding: 8, borderRadius: 6 },
  btnRej: { backgroundColor: '#DC3545', padding: 8, borderRadius: 6 },
  btnPay: { backgroundColor: '#E67E22', padding: 8, borderRadius: 6 },
  btnText: { color: '#FFF', fontWeight: '700', fontSize: 12 },
});
