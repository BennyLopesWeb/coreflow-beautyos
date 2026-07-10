/**
 * AuthGuard
 * Protege rotas autenticadas e redireciona conforme o estado de login.
 */
import React, { ReactNode } from 'react';
import { Redirect } from 'expo-router';
import { useAuth } from '../contexts/AuthContext';
import { Loader } from './Loader';

interface AuthGuardProps {
  /** Se true, exige usuário autenticado; se false, exige usuário deslogado. */
  requireAuth: boolean;
  /** Conteúdo a renderizar quando a condição de auth for satisfeita. */
  children: ReactNode;
  /** Rota de redirecionamento quando a condição não for satisfeita. */
  redirectTo: '/(auth)/login' | '/(tabs)/dashboard' | '/(admin)/dashboard';
}

/**
 * Guarda de autenticação para layouts do Expo Router.
 *
 * @param {AuthGuardProps} props - Propriedades do guard.
 * @returns {JSX.Element} Loader, Redirect ou children.
 */
export const AuthGuard: React.FC<AuthGuardProps> = ({
  requireAuth,
  children,
  redirectTo,
}) => {
  const { loading, isAuthenticated, isAdmin } = useAuth();

  if (loading) {
    return <Loader message="Carregando..." />;
  }

  if (requireAuth && !isAuthenticated) {
    return <Redirect href="/(auth)/login" />;
  }

  if (!requireAuth && isAuthenticated) {
    if (isAdmin) {
      return <Redirect href="/(admin)/dashboard" />;
    }
    return <Redirect href={redirectTo} />;
  }

  return <>{children}</>;
};
