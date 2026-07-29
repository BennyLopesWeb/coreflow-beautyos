import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { trancaService } from '../../../../../src/services/trancaService';
import { Tranca, TrancaImagem } from '../../../../../src/types';
import { ButtonPrimary } from '../../../../../src/components/ButtonPrimary';
import { Loader } from '../../../../../src/components/Loader';
import { TrancaThumbnail } from '../../../../../src/components/TrancaThumbnail';
import {
  formatarDuracao,
  formatarMoeda,
} from '../../../../../src/utils/trancaFormat';
import { irParaAgendar } from '../../../../../src/utils/navigation';
import { ActivationQuoteBlock } from '../../../../../src/components/ActivationQuoteBlock';

/**
 * Detalhes do modelo: preço total, sinal sugerido e mínimo de ativação (se vier da API).
 */
export default function DetalheModeloScreen() {
  const { id, imagemId } = useLocalSearchParams<{ id: string; imagemId: string }>();
  const router = useRouter();
  const [tranca, setTranca] = useState<Tranca | null>(null);
  const [modelo, setModelo] = useState<TrancaImagem | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    loadDados();
  }, [id, imagemId]);

  /**
   * Carrega categoria e modelo específico.
   *
   * @returns {Promise<void>} Promise resolvida após buscar dados.
   */
  const loadDados = async () => {
    try {
      const trancaId = Number(id);
      const modeloId = Number(imagemId);
      const [data, fotos] = await Promise.all([
        trancaService.buscarPorId(trancaId),
        trancaService.listarImagens(trancaId),
      ]);
      const encontrado = fotos.find((f) => f.id === modeloId) ?? null;
      setTranca(data);
      setModelo(encontrado);
    } catch (error) {
      console.error('Erro ao carregar modelo:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <Loader message="Carregando modelo..." />;
  }

  if (!tranca || !modelo) {
    return (
      <View style={styles.container}>
        <Text style={styles.error}>Modelo não encontrado</Text>
      </View>
    );
  }

  const valorRestante =
    modelo.valor_restante ??
    String(
      parseFloat(modelo.valor_total) - parseFloat(modelo.valor_sinal)
    );

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.hero}>
        <TrancaThumbnail
          uri={modelo.url}
          size={160}
          alt={`${tranca.nome} — ${modelo.nome}`}
        />
        <View style={styles.heroInfo}>
          <Text style={styles.categoria}>{tranca.nome}</Text>
          <Text style={styles.title}>{modelo.nome}</Text>
          {modelo.descricao ? (
            <Text style={styles.description}>{modelo.descricao}</Text>
          ) : null}
        </View>
      </View>

      <View style={styles.detailsCard}>
        {modelo.duracao_minutos > 0 && (
          <>
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Tempo estimado</Text>
              <Text style={styles.detailValue}>
                {formatarDuracao(modelo.duracao_minutos)}
              </Text>
            </View>
            <View style={styles.divider} />
          </>
        )}
        {modelo.nivel_complexidade ? (
          <>
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Complexidade</Text>
              <Text style={[styles.detailValue, styles.capitalize]}>
                {modelo.nivel_complexidade}
              </Text>
            </View>
            <View style={styles.divider} />
          </>
        ) : null}
        <View style={styles.detailRow}>
          <Text style={styles.detailLabel}>Valor total</Text>
          <Text style={styles.detailValue}>{formatarMoeda(modelo.valor_total)}</Text>
        </View>
        <View style={styles.divider} />
        <View style={styles.detailRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.detailLabel}>Entrada</Text>
            <ActivationQuoteBlock
              sinalSugerido={modelo.valor_sinal}
              percentualSinal={modelo.percentual_sinal}
              minimumActivationAmount={modelo.minimum_activation_amount}
              minimumActivationCents={modelo.minimum_activation_cents}
            />
          </View>
        </View>
        <View style={styles.divider} />
        <View style={styles.detailRow}>
          <Text style={styles.detailLabel}>Restante (no atendimento)</Text>
          <Text style={styles.detailValue}>{formatarMoeda(valorRestante)}</Text>
        </View>
      </View>

      <Text style={styles.nota}>
        O sinal sugerido é uma cotação comercial. A ativação da reserva depende do
        mínimo financeiro calculado pelo servidor. O saldo restante é pago
        presencialmente.
      </Text>

      <ButtonPrimary
        title="Confirmar Reserva"
        onPress={() => irParaAgendar(router, tranca.id, modelo.id)}
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
  hero: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 16,
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  heroInfo: {
    flex: 1,
    minWidth: 0,
  },
  categoria: {
    fontSize: 13,
    color: '#999',
    fontWeight: '600',
    marginBottom: 4,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: '#333',
    marginBottom: 8,
  },
  description: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
  },
  detailsCard: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
  },
  detailLabel: {
    fontSize: 14,
    color: '#666',
    flex: 1,
    paddingRight: 8,
  },
  detailValue: {
    fontSize: 17,
    fontWeight: '700',
    color: '#333',
  },
  sinal: {
    color: '#7B2CBF',
  },
  capitalize: {
    textTransform: 'capitalize',
  },
  divider: {
    height: 1,
    backgroundColor: '#F0F0F0',
  },
  nota: {
    fontSize: 13,
    color: '#888',
    lineHeight: 20,
    marginBottom: 20,
    textAlign: 'center',
  },
  error: {
    fontSize: 16,
    color: '#DC3545',
    textAlign: 'center',
    marginTop: 40,
  },
});
