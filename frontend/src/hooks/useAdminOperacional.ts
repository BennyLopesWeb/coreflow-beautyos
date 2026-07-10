/**
 * Hook para dados operacionais do painel admin (reservas + fila).
 */
import { useCallback, useState } from 'react';
import { reservationService, Reservation } from '../services/reservationService';
import { adminService } from '../services/adminService';
import { FilaItem } from '../types';

export interface AdminOperacionalData {
  /** Reservas que exigem ação da profissional. */
  reservas: Reservation[];
  /** Itens ativos na fila de espera de hoje. */
  fila: FilaItem[];
  /** Total de pendências (reservas + fila). */
  totalPendencias: number;
  loading: boolean;
  refreshing: boolean;
  /** Recarrega reservas e fila (sem overlay de loading). */
  refresh: () => Promise<void>;
  /** Primeira carga com loading. */
  loadInitial: () => Promise<void>;
}

/**
 * Carrega reservas pendentes e fila do dia para o painel admin.
 *
 * @returns Dados operacionais e funções de atualização.
 */
export function useAdminOperacional(): AdminOperacionalData {
  const [reservas, setReservas] = useState<Reservation[]>([]);
  const [fila, setFila] = useState<FilaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const reload = useCallback(async () => {
    const hoje = new Date().toISOString().split('T')[0];
    try {
      const [reservasData, filaData] = await Promise.all([
        reservationService.listar({ pendentes: true }),
        adminService.consultarFila(hoje),
      ]);
      setReservas(reservasData);
      setFila(
        filaData.posicoes.filter((p) => p.status === 'waiting' || p.status === 'contacted'),
      );
    } catch (error) {
      console.error('Erro ao carregar operacional admin:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    await reload();
  }, [reload]);

  const loadInitial = useCallback(async () => {
    setLoading(true);
    await reload();
  }, [reload]);

  return {
    reservas,
    fila,
    totalPendencias: reservas.length + fila.length,
    loading,
    refreshing,
    refresh,
    loadInitial,
  };
}
