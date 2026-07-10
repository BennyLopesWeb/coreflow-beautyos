import React, { useCallback, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  Image,
} from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { trancaService } from '../../../src/services/trancaService';
import { Tranca } from '../../../src/types';
import { Loader } from '../../../src/components/Loader';

/**
 * Lista tipos de trança para o admin gerenciar álbuns de fotos.
 */
export default function AdminCatalogoScreen() {
  const router = useRouter();
  const [trancas, setTrancas] = useState<Tranca[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async () => {
    try {
      const data = await trancaService.listarAdmin();
      setTrancas(data);
    } catch (error) {
      console.error('Erro ao carregar catálogo:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      loadData();
    }, []),
  );

  if (loading) {
    return <Loader message="Carregando catálogo..." />;
  }

  return (
    <View style={styles.container}>
      <Text style={styles.intro}>
        Gerencie categorias e modelos — cada foto possui preço e duração próprios.
      </Text>
      <TouchableOpacity
        style={styles.novoBtn}
        onPress={() => router.push('/(admin)/catalogo/novo')}
      >
        <Ionicons name="add-circle" size={22} color="#FFF" />
        <Text style={styles.novoBtnText}>Novo tipo de trança</Text>
      </TouchableOpacity>
      <FlatList
        data={trancas}
        keyExtractor={(item) => String(item.id)}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              loadData();
            }}
          />
        }
        ListEmptyComponent={
          <Text style={styles.empty}>Nenhum tipo cadastrado.</Text>
        }
        renderItem={({ item }) => {
          const capa = item.imagens?.filter(Boolean)[0];
          const qtd = item.imagens?.filter(Boolean).length ?? 0;
          return (
            <TouchableOpacity
              style={styles.card}
              onPress={() => router.push(`/(admin)/catalogo/${item.id}`)}
            >
              {capa ? (
                <Image source={{ uri: capa }} style={styles.thumb} />
              ) : (
                <View style={[styles.thumb, styles.thumbPlaceholder]}>
                  <Ionicons name="images-outline" size={28} color="#AAA" />
                </View>
              )}
              <View style={styles.info}>
                <Text style={styles.nome}>{item.nome}</Text>
                <Text style={styles.meta}>
                  {qtd} modelo{qtd !== 1 ? 's' : ''}
                </Text>
                {!item.ativo && (
                  <Text style={styles.inativo}>Inativo</Text>
                )}
              </View>
              <Ionicons name="chevron-forward" size={22} color="#999" />
            </TouchableOpacity>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  intro: {
    padding: 16,
    paddingBottom: 8,
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
    backgroundColor: '#FFF',
  },
  novoBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#7B2CBF',
    marginHorizontal: 16,
    marginBottom: 12,
    paddingVertical: 14,
    borderRadius: 10,
  },
  novoBtnText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '700',
  },
  empty: {
    textAlign: 'center',
    color: '#888',
    marginTop: 40,
  },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF',
    marginHorizontal: 16,
    marginTop: 10,
    padding: 12,
    borderRadius: 10,
    gap: 12,
  },
  thumb: {
    width: 56,
    height: 56,
    borderRadius: 8,
    backgroundColor: '#EEE',
  },
  thumbPlaceholder: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  info: {
    flex: 1,
  },
  nome: {
    fontSize: 16,
    fontWeight: '700',
    color: '#333',
  },
  meta: {
    fontSize: 13,
    color: '#888',
    marginTop: 2,
  },
  inativo: {
    fontSize: 11,
    color: '#DC3545',
    fontWeight: '600',
    marginTop: 4,
  },
});
