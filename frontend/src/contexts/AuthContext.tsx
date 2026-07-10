/**
 * Context de Autenticação
 * Gerencia estado de autenticação e tokens
 */
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import api from '../config/api';
import { getApiErrorMessage } from '../utils/apiError';
import { registerDevicePushToken } from '../services/pushNotificationService';
import { User, LoginRequest, RegisterRequest, TokenResponse } from '../types';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * Hook para acessar o contexto de autenticação.
 *
 * @returns {AuthContextType} Estado e funções de autenticação.
 * @throws {Error} Se usado fora de um AuthProvider.
 */
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth deve ser usado dentro de AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

/**
 * Provider de autenticação. Mantém sessão via AsyncStorage e expõe login/logout.
 *
 * @param {AuthProviderProps} props - Propriedades do provider.
 * @param {ReactNode} props.children - Componentes filhos.
 * @returns {JSX.Element} Provider com o contexto de autenticação.
 */
export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  /**
   * Verifica se existe token salvo e restaura a sessão do usuário.
   *
   * @returns {Promise<void>} Promise resolvida após a verificação.
   */
  const checkAuth = async () => {
    try {
      const token = await AsyncStorage.getItem('access_token');
      if (token) {
        try {
          await refreshUser();
        } catch (error) {
          console.error('Erro ao verificar autenticação:', error);
          await AsyncStorage.multiRemove(['access_token', 'refresh_token']);
        }
      }
    } catch (error) {
      console.error('Erro ao verificar autenticação:', error);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Autentica o usuário com e-mail e senha.
   *
   * @param {LoginRequest} data - Credenciais de login.
   * @returns {Promise<void>} Promise resolvida após login bem-sucedido.
   */
  const login = async (data: LoginRequest) => {
    try {
      const response = await api.post<TokenResponse>('/auth/login', data);
      const { access_token, refresh_token } = response.data;

      await AsyncStorage.multiSet([
        ['access_token', access_token],
        ['refresh_token', refresh_token],
      ]);

      await refreshUser();
    } catch (error: unknown) {
      throw new Error(getApiErrorMessage(error, 'Erro ao fazer login'));
    }
  };

  /**
   * Registra um novo usuário e faz login automaticamente.
   *
   * @param {RegisterRequest} data - Dados de cadastro.
   * @returns {Promise<void>} Promise resolvida após registro e login.
   */
  const register = async (data: RegisterRequest) => {
    try {
      await api.post('/auth/register', {
        ...data,
        email: data.email.trim().toLowerCase(),
      });
      await login({ email: data.email.trim().toLowerCase(), password: data.password });
    } catch (error: unknown) {
      throw new Error(getApiErrorMessage(error, 'Erro ao registrar'));
    }
  };

  /**
   * Encerra a sessão do usuário e remove tokens locais.
   *
   * @returns {Promise<void>} Promise resolvida após logout.
   */
  const logout = async () => {
    try {
      await AsyncStorage.multiRemove(['access_token', 'refresh_token']);
      setUser(null);
    } catch (error) {
      console.error('Erro ao fazer logout:', error);
    }
  };

  /**
   * Atualiza os dados do usuário autenticado a partir da API.
   *
   * @returns {Promise<void>} Promise resolvida após buscar o perfil.
   */
  const refreshUser = async () => {
    try {
      const response = await api.get<User>('/auth/me');
      setUser(response.data);
      if (response.data?.id) {
        registerDevicePushToken(response.data.id).catch(() => undefined);
      }
    } catch (error) {
      await logout();
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated: !!user,
        isAdmin: !!user?.is_superuser,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

