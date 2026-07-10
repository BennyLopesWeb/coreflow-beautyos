import React, { useState } from 'react';
import { View, Text, TextInput, StyleSheet, ScrollView, Alert, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../../src/contexts/AuthContext';
import { ButtonPrimary } from '../../src/components/ButtonPrimary';

/**
 * Exibe alerta compatível com web e mobile.
 *
 * @param {string} title - Título do alerta.
 * @param {string} message - Mensagem do alerta.
 */
function showAlert(title: string, message: string) {
  if (Platform.OS === 'web') {
    window.alert(`${title}\n\n${message}`);
    return;
  }
  Alert.alert(title, message);
}

/**
 * Tela de login do profissional.
 */
export default function LoginScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const router = useRouter();

  /**
   * Autentica o usuário e redireciona para o dashboard.
   */
  const handleLogin = async () => {
    const normalizedEmail = email.trim().toLowerCase();

    if (!normalizedEmail || !password) {
      showAlert('Erro', 'Preencha e-mail e senha');
      return;
    }

    setLoading(true);
    try {
      await login({ email: normalizedEmail, password });
      router.replace('/');
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Erro ao fazer login';
      showAlert('Erro', message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container} keyboardShouldPersistTaps="handled">
      <View style={styles.content}>
        <Text style={styles.title}>BeautyOS</Text>
        <Text style={styles.subtitle}>Gestão inteligente para trancistas</Text>
        <Text style={styles.hint}>Faça login para continuar</Text>

        <TextInput
          style={styles.input}
          placeholder="E-mail"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
          autoCorrect={false}
        />

        <TextInput
          style={styles.input}
          placeholder="Senha"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />

        <ButtonPrimary
          title="Entrar"
          onPress={handleLogin}
          loading={loading}
        />

        <Text
          style={styles.link}
          onPress={() => router.push('/(auth)/register')}
        >
          Não tem conta? Cadastre-se
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFF',
  },
  content: {
    flex: 1,
    padding: 24,
    justifyContent: 'center',
    minHeight: 600,
  },
  title: {
    fontSize: 32,
    fontWeight: '700',
    color: '#7B2CBF',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    marginBottom: 8,
  },
  hint: {
    fontSize: 14,
    color: '#888',
    textAlign: 'center',
    marginBottom: 32,
  },
  input: {
    borderWidth: 1,
    borderColor: '#DDD',
    borderRadius: 8,
    padding: 16,
    fontSize: 16,
    marginBottom: 16,
    backgroundColor: '#FFF',
  },
  link: {
    marginTop: 16,
    textAlign: 'center',
    color: '#7B2CBF',
    fontSize: 14,
  },
});
