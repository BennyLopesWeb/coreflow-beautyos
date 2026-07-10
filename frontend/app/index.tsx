import { Redirect } from 'expo-router';
import { useAuth } from '../src/contexts/AuthContext';
import { Loader } from '../src/components/Loader';

/**
 * Rota inicial: redireciona admin para painel, cliente para tabs, senão login.
 */
export default function Index() {
  const { loading, isAuthenticated, isAdmin } = useAuth();

  if (loading) {
    return <Loader message="Carregando..." />;
  }

  if (isAuthenticated) {
    if (isAdmin) {
      return <Redirect href="/(admin)/dashboard" />;
    }
    return <Redirect href="/(tabs)/dashboard" />;
  }

  return <Redirect href="/(auth)/login" />;
}
