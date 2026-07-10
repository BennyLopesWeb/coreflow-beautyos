import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { financeiroService } from '../../src/services/financeiroService';
import { ResumoFinanceiro, MovimentoFinanceiro } from '../../src/types';
import { Loader } from '../../src/components/Loader';

export default function FinanceiroScreen() {
  const [resumo, setResumo] = useState<ResumoFinanceiro | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadResumo();
  }, []);

  const loadResumo = async () => {
    try {
      const hoje = new Date();
      const inicio = new Date(hoje.getFullYear(), hoje.getMonth(), 1)
        .toISOString()
        .split('T')[0];
      const fim = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0)
        .toISOString()
        .split('T')[0];

      const data = await financeiroService.buscarResumo(inicio, fim);
      setResumo(data);
    } catch (error) {
      console.error('Erro ao carregar resumo:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <Loader message="Carregando resumo financeiro..." />;
  }

  if (!resumo) {
    return (
      <View style={styles.container}>
        <Text style={styles.emptyText}>Nenhum dado financeiro disponível</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Resumo Financeiro</Text>
        <Text style={styles.periodo}>
          {new Date(resumo.inicio).toLocaleDateString('pt-BR')} -{' '}
          {new Date(resumo.fim).toLocaleDateString('pt-BR')}
        </Text>
      </View>

      <View style={styles.resumo}>
        <View style={styles.resumoCard}>
          <Text style={styles.resumoLabel}>Total Entradas</Text>
          <Text style={[styles.resumoValue, styles.entrada]}>
            R$ {parseFloat(resumo.total_entradas).toFixed(2)}
          </Text>
        </View>
        <View style={styles.resumoCard}>
          <Text style={styles.resumoLabel}>Total Saídas</Text>
          <Text style={[styles.resumoValue, styles.saida]}>
            R$ {parseFloat(resumo.total_saidas).toFixed(2)}
          </Text>
        </View>
        <View style={[styles.resumoCard, styles.saldoCard]}>
          <Text style={styles.resumoLabel}>Saldo</Text>
          <Text style={[styles.resumoValue, styles.saldo]}>
            R$ {parseFloat(resumo.saldo).toFixed(2)}
          </Text>
        </View>
      </View>

      <View style={styles.movimentos}>
        <Text style={styles.movimentosTitle}>Movimentações</Text>
        {resumo.movimentos.length === 0 ? (
          <Text style={styles.emptyText}>Nenhuma movimentação</Text>
        ) : (
          resumo.movimentos.map((mov) => (
            <View key={mov.id} style={styles.movimentoItem}>
              <View style={styles.movimentoInfo}>
                <Text style={styles.movimentoDescricao}>{mov.descricao}</Text>
                <Text style={styles.movimentoData}>
                  {new Date(mov.data).toLocaleDateString('pt-BR')}
                </Text>
              </View>
              <Text
                style={[
                  styles.movimentoValor,
                  mov.tipo === 'entrada' ? styles.entrada : styles.saida,
                ]}
              >
                {mov.tipo === 'entrada' ? '+' : '-'}R${' '}
                {parseFloat(mov.valor).toFixed(2)}
              </Text>
            </View>
          ))
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  header: {
    backgroundColor: '#FFF',
    padding: 20,
    marginBottom: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#333',
    marginBottom: 4,
  },
  periodo: {
    fontSize: 14,
    color: '#666',
  },
  resumo: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: 16,
    gap: 12,
  },
  resumoCard: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  },
  saldoCard: {
    width: '100%',
    marginTop: 8,
  },
  resumoLabel: {
    fontSize: 14,
    color: '#666',
    marginBottom: 8,
  },
  resumoValue: {
    fontSize: 24,
    fontWeight: '700',
  },
  entrada: {
    color: '#28A745',
  },
  saida: {
    color: '#DC3545',
  },
  saldo: {
    color: '#7B2CBF',
  },
  movimentos: {
    padding: 16,
  },
  movimentosTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#333',
    marginBottom: 16,
  },
  movimentoItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  movimentoInfo: {
    flex: 1,
  },
  movimentoDescricao: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  movimentoData: {
    fontSize: 12,
    color: '#999',
  },
  movimentoValor: {
    fontSize: 18,
    fontWeight: '700',
  },
  emptyText: {
    fontSize: 16,
    color: '#999',
    textAlign: 'center',
    padding: 40,
  },
});

