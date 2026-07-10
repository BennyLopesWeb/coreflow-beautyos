import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, FlatList } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { trancaService } from '../../../src/services/trancaService';
import { Tranca, TrancaImagem } from '../../../src/types';
import { Loader } from '../../../src/components/Loader';
import { CardModeloTranca } from '../../../src/components/CardModeloTranca';
import { TrancaThumbnail } from '../../../src/components/TrancaThumbnail';
import { irParaAgendar, irParaDetalheModelo } from '../../../src/utils/navigation';

/**
 * Tela da categoria: lista modelos com foto, nome, preço e botão Reservar.
 */
export default function DetalheCategoriaScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [tranca, setTranca] = useState<Tranca | null>(null);
  const [modelos, setModelos] = useState<TrancaImagem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setModelos([]);
    loadDados();
  }, [id]);

  /**
   * Carrega categoria e modelos com preços individuais.
   *
   * @returns {Promise<void>} Promise resolvida após buscar dados.
   */
  const loadDados = async () => {
    try {
      const trancaId = Number(id);
      const [data, fotos] = await Promise.all([
        trancaService.buscarPorId(trancaId),
        trancaService.listarImagens(trancaId),
      ]);
      setTranca(data);
      setModelos(
        fotos.filter(
          (f) =>
            f.ativo !== false &&
            parseFloat(f.valor_total) > 0 &&
            f.duracao_minutos > 0,
        ),
      );
    } catch (error) {
      console.error('Erro ao carregar categoria:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <Loader message="Carregando modelos..." />;
  }

  if (!tranca) {
    return (
      <View style={styles.container}>
        <Text style={styles.error}>Categoria não encontrada</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        {tranca.imagens?.[0] ? (
          <TrancaThumbnail uri={tranca.imagens[0]} size={100} alt={tranca.nome} />
        ) : null}
        <View style={styles.headerText}>
          <Text style={styles.title}>{tranca.nome}</Text>
          {tranca.descricao ? (
            <Text style={styles.description}>{tranca.descricao}</Text>
          ) : null}
        </View>
      </View>

      <Text style={styles.hint}>
        Escolha o modelo — cada um possui preço, duração e sinal próprios
      </Text>

      {modelos.length === 0 ? (
        <Text style={styles.empty}>Nenhum modelo cadastrado nesta categoria.</Text>
      ) : (
        <FlatList
          data={modelos}
          keyExtractor={(item) => String(item.id)}
          scrollEnabled={false}
          renderItem={({ item }) => (
            <CardModeloTranca
              modelo={item}
              categoriaNome={tranca.nome}
              onPress={() => irParaDetalheModelo(router, tranca.id, item.id)}
              onReservar={() => irParaAgendar(router, tranca.id, item.id)}
            />
          )}
        />
      )}
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
    flexDirection: 'row',
    gap: 16,
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    alignItems: 'flex-start',
  },
  headerText: { flex: 1, minWidth: 0 },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#333',
    marginBottom: 8,
  },
  description: {
    fontSize: 15,
    color: '#666',
    lineHeight: 22,
  },
  hint: {
    fontSize: 13,
    color: '#7B2CBF',
    fontWeight: '600',
    marginBottom: 12,
    marginLeft: 4,
  },
  empty: {
    textAlign: 'center',
    color: '#999',
    padding: 24,
    fontSize: 15,
  },
  error: {
    fontSize: 16,
    color: '#DC3545',
    textAlign: 'center',
    marginTop: 40,
  },
});
