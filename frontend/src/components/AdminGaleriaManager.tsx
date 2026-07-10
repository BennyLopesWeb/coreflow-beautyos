/**
 * Gerenciador de álbum de fotos de uma trança (admin).
 */
import React, { useRef, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  Platform,
  ActivityIndicator,
  TextInput,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { Ionicons } from '@expo/vector-icons';
import { TrancaImagem, TrancaImagemUpdate } from '../types';
import { TrancaImagemArquivo } from '../services/trancaService';
import { TrancaThumbnail } from './TrancaThumbnail';
import { MAX_FOTOS_POR_TRANCA } from '../constants/tranca';
import { formatarMoeda, formatarDuracao, calcularSinal, labelPercentualSinal } from '../utils/trancaFormat';

interface AdminGaleriaManagerProps {
  /** Nome da trança (legenda). */
  nome: string;
  /** Fotos atuais do álbum. */
  imagens: TrancaImagem[];
  /** Callback após adicionar foto. */
  onAdicionar: (arquivo: TrancaImagemArquivo) => Promise<void>;
  /** Callback após remover foto. */
  onRemover: (imagemId: number) => Promise<void>;
  /** Callback ao salvar preços de uma foto. */
  onAtualizarPrecos: (imagemId: number, data: TrancaImagemUpdate) => Promise<void>;
  /** Indica operação em andamento. */
  loading?: boolean;
}

/**
 * Exibe alerta compatível web/mobile.
 */
function showConfirm(message: string): Promise<boolean> {
  if (Platform.OS === 'web') {
    return Promise.resolve(window.confirm(message));
  }
  return new Promise((resolve) => {
    Alert.alert('Confirmar', message, [
      { text: 'Cancelar', style: 'cancel', onPress: () => resolve(false) },
      { text: 'Excluir', style: 'destructive', onPress: () => resolve(true) },
    ]);
  });
}

/**
 * Permite ao admin adicionar fotos, definir preços por modelo e excluir do álbum.
 *
 * @param {AdminGaleriaManagerProps} props - Nome, imagens e callbacks.
 * @returns {JSX.Element} Grid de fotos com gestão de preços.
 */
export const AdminGaleriaManager: React.FC<AdminGaleriaManagerProps> = ({
  nome,
  imagens,
  onAdicionar,
  onRemover,
  onAtualizarPrecos,
  loading = false,
}) => {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [uploading, setUploading] = useState(false);
  const [editandoId, setEditandoId] = useState<number | null>(null);
  const [nomeModelo, setNomeModelo] = useState('');
  const [descricaoModelo, setDescricaoModelo] = useState('');
  const [complexidade, setComplexidade] = useState('');
  const [valorTotal, setValorTotal] = useState('');
  const [duracaoHoras, setDuracaoHoras] = useState('');
  const [duracaoMinutos, setDuracaoMinutos] = useState('');
  const [quantidadeTrancas, setQuantidadeTrancas] = useState('');
  const [quantidadeCabelo, setQuantidadeCabelo] = useState('');
  const [percentualSinal, setPercentualSinal] = useState('');
  const [salvandoId, setSalvandoId] = useState<number | null>(null);

  const iniciarEdicao = (img: TrancaImagem) => {
    setEditandoId(img.id);
    setNomeModelo(img.nome);
    setDescricaoModelo(img.descricao ?? '');
    setComplexidade(img.nivel_complexidade ?? '');
    setValorTotal(img.valor_total);
    setDuracaoHoras(String(Math.floor(img.duracao_minutos / 60)));
    setDuracaoMinutos(String(img.duracao_minutos % 60));
    setQuantidadeTrancas(img.quantidade_trancas != null ? String(img.quantidade_trancas) : '');
    setQuantidadeCabelo(img.quantidade_cabelo ?? '');
    setPercentualSinal(
      img.percentual_sinal != null
        ? String(Math.round(parseFloat(img.percentual_sinal) * 100))
        : '',
    );
  };

  const salvarPrecos = async (img: TrancaImagem) => {
    const duracao = (parseInt(duracaoHoras, 10) || 0) * 60 + (parseInt(duracaoMinutos, 10) || 0);
    const pctStr = percentualSinal.trim();
    const percentualPayload = pctStr
      ? String((parseFloat(pctStr.replace(',', '.')) || 0) / 100)
      : undefined;
    setSalvandoId(img.id);
    try {
      await onAtualizarPrecos(img.id, {
        nome: nomeModelo.trim() || undefined,
        descricao: descricaoModelo.trim() || undefined,
        nivel_complexidade: complexidade.trim() || undefined,
        quantidade_trancas: quantidadeTrancas.trim()
          ? parseInt(quantidadeTrancas, 10)
          : undefined,
        quantidade_cabelo: quantidadeCabelo.trim() || undefined,
        valor_total: valorTotal.replace(',', '.'),
        duracao_minutos: duracao,
        percentual_sinal: percentualPayload,
      });
      setEditandoId(null);
    } finally {
      setSalvandoId(null);
    }
  };

  const pctEdicao = percentualSinal.trim()
    ? (parseFloat(percentualSinal.replace(',', '.')) || 0) / 100
    : undefined;

  const handleWebFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await onAdicionar({
        uri: URL.createObjectURL(file),
        name: file.name,
        type: file.type,
        file,
      });
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  const escolherImagem = async () => {
    if (imagens.length >= MAX_FOTOS_POR_TRANCA) {
      Alert.alert('Limite atingido', `Máximo ${MAX_FOTOS_POR_TRANCA} fotos por tipo.`);
      return;
    }
    if (Platform.OS === 'web') {
      inputRef.current?.click();
      return;
    }
    const permissao = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permissao.granted) return;
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.85,
    });
    if (result.canceled || !result.assets?.length) return;
    const asset = result.assets[0];
    setUploading(true);
    try {
      await onAdicionar({
        uri: asset.uri,
        name: `foto.${asset.uri.split('.').pop() || 'jpg'}`,
        type: asset.mimeType || 'image/jpeg',
      });
    } finally {
      setUploading(false);
    }
  };

  const handleRemover = async (img: TrancaImagem) => {
    const ok = await showConfirm(`Excluir ${img.label} de "${nome}"?`);
    if (!ok) return;
    await onRemover(img.id);
  };

  const busy = loading || uploading;
  const limiteAtingido = imagens.length >= MAX_FOTOS_POR_TRANCA;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Álbum de fotos / modelos</Text>
        <Text style={styles.subtitle}>
          {imagens.length}/{MAX_FOTOS_POR_TRANCA} — cada foto com valor e duração próprios (sinal {labelPercentualSinal()} automático)
        </Text>
      </View>

      <View style={styles.grid}>
        {imagens.map((img) => (
          <View key={img.id} style={styles.card}>
            <TrancaThumbnail uri={img.url} size={90} alt={`${nome} — ${img.label}`} />
            <Text style={styles.label}>{img.nome}</Text>

            {editandoId === img.id ? (
              <View style={styles.editBox}>
                <TextInput
                  style={styles.input}
                  value={nomeModelo}
                  onChangeText={setNomeModelo}
                  placeholder="Nome do modelo"
                />
                <TextInput
                  style={styles.input}
                  value={descricaoModelo}
                  onChangeText={setDescricaoModelo}
                  placeholder="Descrição"
                  multiline
                />
                <TextInput
                  style={styles.input}
                  value={complexidade}
                  onChangeText={setComplexidade}
                  placeholder="Complexidade (baixa/media/alta)"
                />
                <TextInput
                  style={styles.input}
                  value={quantidadeTrancas}
                  onChangeText={setQuantidadeTrancas}
                  placeholder="Qtd. tranças"
                  keyboardType="number-pad"
                />
                <TextInput
                  style={styles.input}
                  value={quantidadeCabelo}
                  onChangeText={setQuantidadeCabelo}
                  placeholder="Qtd. cabelo (ex: 6 pacotes)"
                />
                <TextInput
                  style={styles.input}
                  value={valorTotal}
                  onChangeText={setValorTotal}
                  placeholder="Preço total R$"
                  keyboardType="decimal-pad"
                />
                <TextInput
                  style={styles.input}
                  value={percentualSinal}
                  onChangeText={setPercentualSinal}
                  placeholder={`Sinal % (padrão ${labelPercentualSinal()})`}
                  keyboardType="decimal-pad"
                />
                {valorTotal ? (
                  <Text style={styles.sinalPreview}>
                    Sinal ({labelPercentualSinal(pctEdicao)}): {formatarMoeda(calcularSinal(valorTotal.replace(',', '.'), pctEdicao))}
                  </Text>
                ) : null}
                <View style={styles.row}>
                  <TextInput
                    style={[styles.input, styles.inputSmall]}
                    value={duracaoHoras}
                    onChangeText={setDuracaoHoras}
                    placeholder="h"
                    keyboardType="number-pad"
                  />
                  <TextInput
                    style={[styles.input, styles.inputSmall]}
                    value={duracaoMinutos}
                    onChangeText={setDuracaoMinutos}
                    placeholder="min"
                    keyboardType="number-pad"
                  />
                </View>
                <TouchableOpacity
                  style={styles.saveBtn}
                  onPress={() => salvarPrecos(img)}
                  disabled={salvandoId === img.id}
                >
                  <Text style={styles.saveBtnText}>
                    {salvandoId === img.id ? '...' : 'Salvar'}
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity onPress={() => setEditandoId(null)}>
                  <Text style={styles.cancelText}>Cancelar</Text>
                </TouchableOpacity>
              </View>
            ) : (
              <>
                <Text style={styles.preco}>{formatarMoeda(img.valor_total)}</Text>
                <Text style={styles.sinal}>
                  Sinal {labelPercentualSinal(img.percentual_sinal)}: {formatarMoeda(img.valor_sinal)}
                </Text>
                {img.quantidade_trancas != null ? (
                  <Text style={styles.meta}>Tranças: {img.quantidade_trancas}</Text>
                ) : null}
                {img.quantidade_cabelo ? (
                  <Text style={styles.meta}>Cabelo: {img.quantidade_cabelo}</Text>
                ) : null}
                <Text style={styles.restante}>
                  Restante: {formatarMoeda(img.valor_restante ?? String(parseFloat(img.valor_total) - parseFloat(img.valor_sinal)))}
                </Text>
                <Text style={styles.duracao}>{formatarDuracao(img.duracao_minutos)}</Text>
                <TouchableOpacity onPress={() => iniciarEdicao(img)} disabled={busy}>
                  <Text style={styles.editLink}>Editar valores</Text>
                </TouchableOpacity>
              </>
            )}

            <TouchableOpacity style={styles.deleteBtn} onPress={() => handleRemover(img)} disabled={busy}>
              <Ionicons name="trash-outline" size={16} color="#DC3545" />
              <Text style={styles.deleteText}>Excluir</Text>
            </TouchableOpacity>
          </View>
        ))}

        {!limiteAtingido && (
          <TouchableOpacity
            style={[styles.addCard, busy && styles.addCardDisabled]}
            onPress={escolherImagem}
            disabled={busy}
          >
            {uploading ? (
              <ActivityIndicator color="#7B2CBF" />
            ) : (
              <>
                <Ionicons name="add-circle-outline" size={36} color="#7B2CBF" />
                <Text style={styles.addText}>Adicionar foto</Text>
              </>
            )}
          </TouchableOpacity>
        )}
      </View>

      {imagens.length === 0 && (
        <Text style={styles.emptyHint}>
          Adicione fotos e defina o valor de cada modelo (dificuldade diferente).
        </Text>
      )}

      {Platform.OS === 'web' && (
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          style={{ display: 'none' }}
          onChange={handleWebFile}
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: { marginBottom: 16 },
  header: { marginBottom: 12 },
  title: { fontSize: 18, fontWeight: '700', color: '#333' },
  subtitle: { fontSize: 13, color: '#888', marginTop: 4 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  card: {
    alignItems: 'center',
    backgroundColor: '#FFF',
    borderRadius: 10,
    padding: 10,
    width: 140,
    borderWidth: 1,
    borderColor: '#EEE',
  },
  label: { fontSize: 12, fontWeight: '700', color: '#666', marginTop: 6 },
  preco: { fontSize: 14, fontWeight: '700', color: '#333', marginTop: 4 },
  sinal: { fontSize: 12, color: '#7B2CBF', fontWeight: '600' },
  restante: { fontSize: 11, color: '#888', marginTop: 2 },
  sinalPreview: { fontSize: 11, color: '#7B2CBF', marginBottom: 6, fontWeight: '600' },
  duracao: { fontSize: 11, color: '#888', marginTop: 2 },
  meta: { fontSize: 10, color: '#999', marginTop: 2 },
  editLink: { fontSize: 11, color: '#7B2CBF', fontWeight: '700', marginTop: 6 },
  editBox: { width: '100%', marginTop: 4 },
  input: {
    borderWidth: 1,
    borderColor: '#DDD',
    borderRadius: 6,
    padding: 6,
    fontSize: 12,
    marginBottom: 4,
    backgroundColor: '#FAFAFA',
  },
  inputSmall: { flex: 1 },
  row: { flexDirection: 'row', gap: 4 },
  saveBtn: {
    backgroundColor: '#7B2CBF',
    borderRadius: 6,
    padding: 6,
    alignItems: 'center',
    marginTop: 2,
  },
  saveBtnText: { color: '#FFF', fontSize: 12, fontWeight: '700' },
  cancelText: { fontSize: 11, color: '#888', textAlign: 'center', marginTop: 4 },
  deleteBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 8 },
  deleteText: { fontSize: 11, color: '#DC3545', fontWeight: '600' },
  addCard: {
    width: 140,
    height: 180,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: '#7B2CBF',
    borderStyle: 'dashed',
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#FAFAFA',
  },
  addCardDisabled: { opacity: 0.6 },
  addText: { fontSize: 12, color: '#7B2CBF', fontWeight: '600', marginTop: 6, textAlign: 'center' },
  emptyHint: { fontSize: 13, color: '#999', marginTop: 12, textAlign: 'center', lineHeight: 20 },
});
