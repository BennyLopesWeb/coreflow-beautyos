import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Alert, Platform } from 'react-native';
import { useLocalSearchParams, useFocusEffect } from 'expo-router';
import { trancaService } from '../../../src/services/trancaService';
import { Tranca, TrancaImagem, TrancaImagemUpdate } from '../../../src/types';
import { Loader } from '../../../src/components/Loader';
import { AdminGaleriaManager } from '../../../src/components/AdminGaleriaManager';
import { TrancaForm, TrancaFormData } from '../../../src/components/TrancaForm';
import { getApiErrorMessage } from '../../../src/utils/apiError';

/**
 * Exibe alerta compatível web/mobile.
 */
function showAlert(title: string, message: string) {
  if (Platform.OS === 'web') {
    window.alert(`${title}\n\n${message}`);
    return;
  }
  Alert.alert(title, message);
}

/**
 * Tela admin para editar dados e gerenciar álbum de um tipo de trança.
 */
export default function AdminCatalogoDetalheScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [tranca, setTranca] = useState<Tranca | null>(null);
  const [imagens, setImagens] = useState<TrancaImagem[]>([]);
  const [loading, setLoading] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [editando, setEditando] = useState(false);

  const trancaId = Number(id);

  const loadData = async () => {
    try {
      const [t, imgs] = await Promise.all([
        trancaService.buscarPorId(trancaId),
        trancaService.listarImagens(trancaId),
      ]);
      setTranca(t);
      setImagens(imgs);
    } catch (error) {
      showAlert('Erro', getApiErrorMessage(error, 'Falha ao carregar tipo'));
    } finally {
      setLoading(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      setImagens([]);
      loadData();
    }, [id]),
  );

  /**
   * Atualiza nome, descrição e valores do tipo.
   */
  const handleSalvarDados = async (form: TrancaFormData) => {
    setSalvando(true);
    try {
      const atualizada = await trancaService.atualizar(trancaId, {
        nome: form.nome.trim(),
        descricao: form.descricao.trim() || undefined,
        ativo: form.ativo,
      });
      setTranca(atualizada);
      setEditando(false);
      showAlert('Sucesso', 'Dados atualizados.');
    } catch (error) {
      showAlert('Erro', getApiErrorMessage(error, 'Falha ao salvar'));
    } finally {
      setSalvando(false);
    }
  };

  /**
   * Envia nova foto para o álbum da trança.
   */
  const handleAdicionar = async (arquivo: Parameters<typeof trancaService.adicionarImagem>[1]) => {
    try {
      const atualizadas = await trancaService.adicionarImagem(trancaId, arquivo);
      setImagens(atualizadas);
      const t = await trancaService.buscarPorId(trancaId);
      setTranca(t);
      showAlert('Sucesso', 'Foto adicionada ao álbum.');
    } catch (error) {
      showAlert('Erro', getApiErrorMessage(error, 'Falha ao adicionar foto'));
    }
  };

  /**
   * Remove foto do álbum da trança.
   */
  const handleRemover = async (imagemId: number) => {
    try {
      const atualizadas = await trancaService.removerImagem(trancaId, imagemId);
      setImagens(atualizadas);
      const t = await trancaService.buscarPorId(trancaId);
      setTranca(t);
      showAlert('Sucesso', 'Foto removida do álbum.');
    } catch (error) {
      showAlert('Erro', getApiErrorMessage(error, 'Falha ao remover foto'));
    }
  };

  /**
   * Atualiza preços e duração de uma foto/modelo.
   */
  const handleAtualizarPrecos = async (imagemId: number, data: TrancaImagemUpdate) => {
    try {
      const atualizada = await trancaService.atualizarImagem(trancaId, imagemId, data);
      setImagens((prev) => prev.map((i) => (i.id === imagemId ? atualizada : i)));
      showAlert('Sucesso', 'Valores do modelo atualizados.');
    } catch (error) {
      showAlert('Erro', getApiErrorMessage(error, 'Falha ao salvar valores'));
    }
  };

  if (loading || !tranca) {
    return <Loader message="Carregando..." />;
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <Text style={styles.sectionTitle}>Dados da categoria</Text>
        {!editando ? (
          <>
            <Text style={styles.nome}>{tranca.nome}</Text>
            {tranca.descricao ? (
              <Text style={styles.desc}>{tranca.descricao}</Text>
            ) : null}
            <Text style={styles.status}>
              {tranca.ativo ? '✓ Visível no catálogo' : '✗ Oculta do catálogo'}
            </Text>
            <Text style={styles.hintCat}>
              Preços e durações são definidos em cada modelo abaixo.
            </Text>
            <Text style={styles.editLink} onPress={() => setEditando(true)}>
              Editar dados
            </Text>
          </>
        ) : (
          <>
            <TrancaForm
              initial={tranca}
              submitLabel="Salvar alterações"
              onSubmit={handleSalvarDados}
              loading={salvando}
            />
            <Text style={styles.cancelLink} onPress={() => setEditando(false)}>
              Cancelar edição
            </Text>
          </>
        )}
      </View>

      <AdminGaleriaManager
        nome={tranca.nome}
        imagens={imagens}
        onAdicionar={handleAdicionar}
        onRemover={handleRemover}
        onAtualizarPrecos={handleAtualizarPrecos}
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  content: {
    padding: 16,
    paddingBottom: 32,
  },
  header: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: '#7B2CBF',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 8,
  },
  nome: {
    fontSize: 22,
    fontWeight: '700',
    color: '#333',
  },
  desc: {
    fontSize: 14,
    color: '#666',
    marginTop: 6,
    lineHeight: 20,
  },
  details: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginTop: 10,
  },
  detailItem: {
    fontSize: 13,
    color: '#888',
    fontWeight: '600',
  },
  status: {
    fontSize: 13,
    color: '#666',
    marginTop: 10,
  },
  hintCat: {
    fontSize: 13,
    color: '#7B2CBF',
    marginTop: 8,
    fontWeight: '600',
  },
  editLink: {
    fontSize: 14,
    color: '#7B2CBF',
    fontWeight: '700',
    marginTop: 12,
  },
  cancelLink: {
    fontSize: 14,
    color: '#888',
    textAlign: 'center',
    marginTop: 12,
  },
});
