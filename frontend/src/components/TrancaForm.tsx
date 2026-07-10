/**
 * Formulário de cadastro/edição de categoria de trança (admin).
 * Categoria agrupa modelos — sem preço, duração ou sinal.
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  Switch,
} from 'react-native';
import { Tranca } from '../types';
import { ButtonPrimary } from './ButtonPrimary';

/** Dados do formulário de categoria. */
export interface TrancaFormData {
  nome: string;
  descricao: string;
  ativo: boolean;
}

interface TrancaFormProps {
  /** Valores iniciais (edição). */
  initial?: Tranca | null;
  /** Texto do botão de envio. */
  submitLabel?: string;
  /** Callback ao salvar dados válidos. */
  onSubmit: (data: TrancaFormData) => Promise<void>;
  /** Indica envio em andamento. */
  loading?: boolean;
}

/**
 * Converte Tranca em valores do formulário.
 *
 * @param {Tranca | null | undefined} tranca - Categoria existente ou null.
 * @returns {TrancaFormData} Valores iniciais do formulário.
 */
export function trancaParaForm(tranca?: Tranca | null): TrancaFormData {
  if (!tranca) {
    return { nome: '', descricao: '', ativo: true };
  }
  return {
    nome: tranca.nome,
    descricao: tranca.descricao ?? '',
    ativo: tranca.ativo,
  };
}

/**
 * Formulário para criar ou editar categoria (sem dados comerciais).
 *
 * @param {TrancaFormProps} props - Valores iniciais, rótulo e callback.
 * @returns {JSX.Element} Formulário de categoria.
 */
export const TrancaForm: React.FC<TrancaFormProps> = ({
  initial,
  submitLabel = 'Salvar',
  onSubmit,
  loading = false,
}) => {
  const [form, setForm] = useState<TrancaFormData>(() => trancaParaForm(initial));
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    setForm(trancaParaForm(initial));
  }, [initial?.id]);

  const atualizar = (campo: keyof TrancaFormData, valor: string | boolean) => {
    setForm((prev) => ({ ...prev, [campo]: valor }));
    setErro(null);
  };

  /**
   * Valida e envia o formulário.
   */
  const handleSubmit = async () => {
    if (!form.nome.trim()) {
      setErro('Informe o nome da categoria.');
      return;
    }
    await onSubmit(form);
  };

  return (
    <View style={styles.container}>
      <Text style={styles.label}>Nome da categoria *</Text>
      <TextInput
        style={styles.input}
        value={form.nome}
        onChangeText={(v) => atualizar('nome', v)}
        placeholder="Ex: Box Braids, Trança Tiara Raiz..."
      />

      <Text style={styles.label}>Descrição</Text>
      <TextInput
        style={[styles.input, styles.textArea]}
        value={form.descricao}
        onChangeText={(v) => atualizar('descricao', v)}
        placeholder="Descreva o estilo em geral (opcional)"
        multiline
        numberOfLines={4}
        textAlignVertical="top"
      />

      <Text style={styles.hint}>
        Preço, duração e sinal são definidos em cada modelo (foto) abaixo.
      </Text>

      <View style={styles.switchRow}>
        <Text style={styles.label}>Visível no catálogo</Text>
        <Switch
          value={form.ativo}
          onValueChange={(v) => atualizar('ativo', v)}
          trackColor={{ false: '#CCC', true: '#C9A0E8' }}
          thumbColor={form.ativo ? '#7B2CBF' : '#F4F4F4'}
        />
      </View>

      {erro ? <Text style={styles.erro}>{erro}</Text> : null}

      <ButtonPrimary title={submitLabel} onPress={handleSubmit} loading={loading} />
    </View>
  );
};

const styles = StyleSheet.create({
  container: { gap: 4 },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#444',
    marginTop: 8,
    marginBottom: 4,
  },
  input: {
    borderWidth: 1,
    borderColor: '#DDD',
    borderRadius: 8,
    padding: 14,
    fontSize: 16,
    backgroundColor: '#FFF',
  },
  textArea: { minHeight: 100, paddingTop: 14 },
  hint: {
    fontSize: 13,
    color: '#7B2CBF',
    lineHeight: 20,
    marginVertical: 8,
    fontWeight: '600',
  },
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginVertical: 8,
  },
  erro: { color: '#DC3545', fontSize: 14, marginVertical: 8 },
});
