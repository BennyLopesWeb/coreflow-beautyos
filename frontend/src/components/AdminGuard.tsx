/**
 * AdminGuard
 * Protege rotas administrativas — exige is_superuser.
 */
import React, { ReactNode } from 'react';
import { Redirect } from 'expo-router';
import { useAuth } from '../contexts/AuthContext';
import { Loader } from './Loader';

interface AdminGuardProps {
  /** Conteúdo a renderizar quando o usuário for admin. */
  children: ReactNode;
}

/**
 * Guarda de rotas admin. Redireciona não-admins para o app cliente.
 *
 * @param {AdminGuardProps} props - Propriedades do guard.
 * @returns {JSX.Element} Loader, Redirect ou children.
 */
export const AdminGuard: React.FC<AdminGuardProps> = ({ children }) => {
  const { loading, isAuthenticated, isAdmin } = useAuth();

  if (loading) {
    return <Loader message="Carregando..." />;
  }

  if (!isAuthenticated) {
    return <Redirect href="/(auth)/login" />;
  }

  if (!isAdmin) {
    return <Redirect href="/(tabs)/dashboard" />;
  }

  return <>{children}</>;
};
