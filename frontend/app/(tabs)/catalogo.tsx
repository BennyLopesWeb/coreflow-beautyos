import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, FlatList, RefreshControl } from 'react-native';
import { useRouter } from 'expo-router';
import { trancaService } from '../../src/services/trancaService';
import { CardTranca } from '../../src/components/CardTranca';
import { Loader } from '../../src/components/Loader';
import { Tranca } from '../../src/types';

export default function CatalogoScreen() {
  const [trancas, setTrancas] = useState<Tranca[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const router = useRouter();

  const loadTrancas = async () => {
    try {
      const data = await trancaService.listar();
      setTrancas(data.filter(t => t.ativo));
    } catch (error) {
      console.error('Erro ao carregar tranças:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadTrancas();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    loadTrancas();
  };

  if (loading) {
    return <Loader message="Carregando catálogo..." />;
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Catálogo de Tranças</Text>
      <FlatList
        data={trancas}
        keyExtractor={(item) => item.id.toString()}
        renderItem={({ item }) => (
          <CardTranca
            tranca={item}
            onPress={() => router.push(`/(tabs)/detalhe/${item.id}`)}
          />
        )}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyText}>Nenhuma trança disponível</Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#333',
    padding: 16,
    backgroundColor: '#FFF',
  },
  list: {
    padding: 16,
  },
  empty: {
    padding: 40,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 16,
    color: '#999',
  },
});

