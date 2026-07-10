/**
 * Contexto operacional do admin — badges e refresh compartilhado entre abas.
 */
import React, { createContext, useContext, ReactNode, useEffect } from 'react';
import { useAdminOperacional, AdminOperacionalData } from '../hooks/useAdminOperacional';

const AdminOperacionalContext = createContext<AdminOperacionalData | null>(null);

interface AdminOperacionalProviderProps {
  children: ReactNode;
}

/**
 * Provider que mantém reservas/fila atualizadas para o painel admin.
 *
 * @param props - Componentes filhos.
 * @returns Provider com dados operacionais.
 */
export function AdminOperacionalProvider({ children }: AdminOperacionalProviderProps) {
  const operacional = useAdminOperacional();

  useEffect(() => {
    operacional.loadInitial();
  }, []);

  return (
    <AdminOperacionalContext.Provider value={operacional}>
      {children}
    </AdminOperacionalContext.Provider>
  );
}

/**
 * Acessa dados operacionais do admin (reservas pendentes + fila).
 *
 * @returns Dados operacionais ou valores vazios se fora do provider.
 */
export function useAdminOperacionalContext(): AdminOperacionalData {
  const ctx = useContext(AdminOperacionalContext);
  if (!ctx) {
    return {
      reservas: [],
      fila: [],
      totalPendencias: 0,
      loading: false,
      refreshing: false,
      refresh: async () => {},
      loadInitial: async () => {},
    };
  }
  return ctx;
}

/**
 * Formata badge numérico para a tab bar (máx. 99+).
 *
 * @param count - Quantidade a exibir.
 * @returns String do badge ou undefined se zero.
 */
export function formatTabBadge(count: number): string | undefined {
  if (count <= 0) return undefined;
  return count > 99 ? '99+' : String(count);
}
