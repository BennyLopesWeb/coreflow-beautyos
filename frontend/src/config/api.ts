/**
 * Configuração da API
 * Cliente Axios para comunicação com backend
 */
import axios from 'axios';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

/**
 * Retorna a URL base da API conforme a plataforma em execução.
 * Web usa localhost; mobile físico precisa do IP da máquina na rede local.
 */
function getApiBaseUrl(): string {
  const fromEnv = process.env.EXPO_PUBLIC_API_URL;
  if (fromEnv) {
    return fromEnv.replace(/\/$/, '');
  }
  if (!__DEV__) {
    return 'https://api.trancapro.com';
  }
  if (Platform.OS === 'web') {
    return 'http://localhost:8000';
  }
  // Ajuste o IP abaixo para o IP da sua máquina na rede local
  return 'http://192.168.0.6:8000';
}

const API_BASE_URL = getApiBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para adicionar token
api.interceptors.request.use(
  async (config) => {
    const token = await AsyncStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor para refresh token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        const refreshToken = await AsyncStorage.getItem('refresh_token');
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          
          const { access_token } = response.data;
          await AsyncStorage.setItem('access_token', access_token);
          
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        // Refresh falhou, fazer logout
        await AsyncStorage.multiRemove(['access_token', 'refresh_token']);
        // Redirecionar para login
      }
    }
    
    return Promise.reject(error);
  }
);

export default api;

