import React, { useState } from 'react';
import { View, Text, TextInput, StyleSheet, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../../src/contexts/AuthContext';
import { ButtonPrimary } from '../../src/components/ButtonPrimary';
import { showAlert } from '../../src/utils/alert';
import { telefoneValido } from '../../src/utils/telefone';

/**
 * Tela de cadastro de novo usuário profissional.
 */
export default function RegisterScreen() {
  const [nome, setNome] = useState('');
  const [email, setEmail] = useState('');
  const [telefone, setTelefone] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const router = useRouter();

  /**
   * Valida os campos e envia o cadastro para a API.
   */
  const handleRegister = async () => {
    const normalizedEmail = email.trim().toLowerCase();

    if (!normalizedEmail || !nome.trim() || !password || !telefone.trim()) {
      showAlert('Erro', 'Preencha nome, e-mail, telefone e senha');
      return;
    }

    if (!telefoneValido(telefone)) {
      showAlert('Erro', 'Informe um telefone válido (mínimo 10 dígitos)');
      return;
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
      showAlert('Erro', 'Informe um e-mail válido');
      return;
    }

    if (password !== confirmPassword) {
      showAlert('Erro', 'As senhas não coincidem');
      return;
    }

    if (password.length < 6) {
      showAlert('Erro', 'A senha deve ter pelo menos 6 caracteres');
      return;
    }

    setLoading(true);
    try {
      await register({
        email: normalizedEmail,
        nome: nome.trim(),
        password,
        telefone: telefone.trim(),
      });
      router.replace('/(tabs)/dashboard');
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Erro ao registrar';
      showAlert('Erro', message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container} keyboardShouldPersistTaps="handled">
      <View style={styles.content}>
        <Text style={styles.title}>Criar Conta</Text>
        <Text style={styles.subtitle}>Cadastre-se no BeautyOS</Text>

        <TextInput
          style={styles.input}
          placeholder="Nome completo *"
          value={nome}
          onChangeText={setNome}
          autoCapitalize="words"
        />

        <TextInput
          style={styles.input}
          placeholder="E-mail *"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
          autoCorrect={false}
        />

        <TextInput
          style={styles.input}
          placeholder="Telefone *"
          value={telefone}
          onChangeText={setTelefone}
          keyboardType="phone-pad"
        />

        <TextInput
          style={styles.input}
          placeholder="Senha *"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />

        <TextInput
          style={styles.input}
          placeholder="Confirmar senha *"
          value={confirmPassword}
          onChangeText={setConfirmPassword}
          secureTextEntry
        />

        <ButtonPrimary
          title="Cadastrar"
          onPress={handleRegister}
          loading={loading}
        />

        <Text
          style={styles.link}
          onPress={() => router.push('/(auth)/login')}
        >
          Já tem conta? Faça login
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
