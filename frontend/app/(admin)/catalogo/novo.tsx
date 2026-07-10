import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Alert, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { trancaService } from '../../../src/services/trancaService';
import { TrancaForm, TrancaFormData } from '../../../src/components/TrancaForm';
import { getApiErrorMessage } from '../../../src/utils/apiError';

function showAlert(title: string, message: string) {
  if (Platform.OS === 'web') {
    window.alert(`${title}\n\n${message}`);
    return;
  }
  Alert.alert(title, message);
}

/**
 * Tela admin para cadastrar nova categoria de trança.
 */
export default function AdminCatalogoNovoScreen() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);

  const handleCriar = async (form: TrancaFormData) => {
    setSubmitting(true);
    try {
      const tranca = await trancaService.criar({
        nome: form.nome.trim(),
        descricao: form.descricao.trim() || undefined,
        imagens: [],
        ativo: form.ativo,
      });

      if (Platform.OS === 'web') {
        const ir = window.confirm(
          `Categoria "${tranca.nome}" criada!\n\nAdicionar modelos (fotos com preço) agora?`,
        );
        if (ir) router.replace(`/(admin)/catalogo/${tranca.id}`);
        else router.back();
        return;
      }

      Alert.alert('Categoria criada', `"${tranca.nome}" cadastrada.`, [
        {
          text: 'Adicionar modelos',
          onPress: () => router.replace(`/(admin)/catalogo/${tranca.id}`),
        },
        { text: 'Depois', style: 'cancel', onPress: () => router.back() },
      ]);
    } catch (error) {
      showAlert('Erro', getApiErrorMessage(error, 'Falha ao criar categoria'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.intro}>
        Cadastre a categoria (nome e descrição). Depois adicione modelos com foto,
        preço e duração individual.
      </Text>
      <View style={styles.card}>
        <TrancaForm submitLabel="Criar categoria" onSubmit={handleCriar} loading={submitting} />
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5' },
  content: { padding: 16, paddingBottom: 32 },
  intro: { fontSize: 14, color: '#666', lineHeight: 20, marginBottom: 16 },
  card: { backgroundColor: '#FFF', borderRadius: 12, padding: 16 },
});
