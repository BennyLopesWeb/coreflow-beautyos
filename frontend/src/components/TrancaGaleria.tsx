/**
 * Galeria de fotos de uma trança (Foto 1, Foto 2, ... Foto N).
 */
import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
} from 'react-native';
import { TrancaImagem } from '../types';
import { TrancaThumbnail } from './TrancaThumbnail';
import { formatarMoeda, formatarDuracao, labelPercentualSinal } from '../utils/trancaFormat';

interface TrancaGaleriaProps {
  /** Fotos com ID (preferencial — usado na reserva). */
  itens?: TrancaImagem[];
  /** Lista de URLs (legado / fallback). */
  imagens?: string[];
  /** Nome da trança (legenda / alt). */
  nome: string;
  /** Tamanho da foto principal em pixels. */
  mainSize?: number;
  /** Modo seleção para reserva. */
  selectable?: boolean;
  /** ID da foto selecionada (modo seleção). */
  selectedId?: number;
  /** Callback ao selecionar foto (modo seleção). */
  onSelect?: (item: TrancaImagem) => void;
}

/**
 * Normaliza props em lista de TrancaImagem.
 *
 * @param {TrancaImagem[] | undefined} itens - Itens com ID.
 * @param {string[] | undefined} imagens - URLs fallback.
 * @returns {TrancaImagem[]} Lista unificada de fotos.
 */
function normalizarItens(itens?: TrancaImagem[], imagens?: string[]): TrancaImagem[] {
  if (itens && itens.length > 0) {
    return itens;
  }
  return (imagens ?? [])
    .filter(Boolean)
    .map((url, i) => ({
      id: -(i + 1),
      url,
      ordem: i + 1,
      is_principal: i === 0,
      label: `Foto ${i + 1}`,
      nome: `Foto ${i + 1}`,
      valor_total: '0',
      valor_sinal: '0',
      valor_restante: '0',
      duracao_minutos: 0,
    }));
}

/**
 * Exibe galeria com foto principal selecionável e miniaturas numeradas.
 *
 * @param {TrancaGaleriaProps} props - URLs ou itens, nome e opções de seleção.
 * @returns {JSX.Element} Galeria com seleção de foto e zoom.
 */
export const TrancaGaleria: React.FC<TrancaGaleriaProps> = ({
  itens,
  imagens,
  nome,
  mainSize = 130,
  selectable = false,
  selectedId,
  onSelect,
}) => {
  const fotos = normalizarItens(itens, imagens);
  const [indice, setIndice] = useState(0);

  useEffect(() => {
    if (selectedId != null && fotos.length > 0) {
      const idx = fotos.findIndex((f) => f.id === selectedId);
      if (idx >= 0) {
        setIndice(idx);
      }
    }
  }, [selectedId, fotos]);

  if (fotos.length === 0) {
    return (
      <View style={[styles.placeholder, { width: mainSize, height: mainSize }]}>
        <Text style={styles.placeholderText}>Sem foto</Text>
      </View>
    );
  }

  const indiceAtual = Math.min(indice, fotos.length - 1);
  const fotoAtual = fotos[indiceAtual];

  const handleSelect = (item: TrancaImagem, i: number) => {
    setIndice(i);
    if (selectable && onSelect) {
      onSelect(item);
    }
  };

  return (
    <View style={styles.container}>
      <TrancaThumbnail
        uri={fotoAtual.url}
        size={mainSize}
        alt={`${nome} — ${fotoAtual.label}`}
      />

      {fotos.length > 1 && (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.thumbsScroll}
          contentContainerStyle={styles.thumbsContent}
        >
          {fotos.map((item, i) => {
            const ativo = i === indiceAtual;
            return (
              <TouchableOpacity
                key={item.id}
                style={[styles.thumbItem, ativo && styles.thumbItemActive]}
                onPress={() => handleSelect(item, i)}
              >
                <Image source={{ uri: item.url }} style={styles.miniThumb} resizeMode="cover" />
                <Text style={[styles.thumbLabel, ativo && styles.thumbLabelActive]}>
                  {item.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      )}

      {fotos.length === 1 && (
        <Text style={styles.singleLabel}>{fotos[0].label}</Text>
      )}

      {selectable && fotoAtual.valor_total && (
        <View style={styles.precoBox}>
          <Text style={styles.precoTotal}>{formatarMoeda(fotoAtual.valor_total)}</Text>
          <Text style={styles.precoSinal}>
            Sinal {labelPercentualSinal()}: {formatarMoeda(fotoAtual.valor_sinal)}
          </Text>
          {fotoAtual.duracao_minutos > 0 && (
            <Text style={styles.precoDuracao}>
              {formatarDuracao(fotoAtual.duracao_minutos)}
            </Text>
          )}
        </View>
      )}

      {selectable && (
        <Text style={styles.selectHint}>
          Cada foto pode ter valor e dificuldade diferentes
        </Text>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    maxWidth: 160,
  },
  placeholder: {
    borderRadius: 10,
    backgroundColor: '#EEE',
    justifyContent: 'center',
    alignItems: 'center',
  },
  placeholderText: {
    fontSize: 12,
    color: '#999',
  },
  thumbsScroll: {
    marginTop: 8,
    maxWidth: 160,
  },
  thumbsContent: {
    gap: 6,
    paddingVertical: 4,
  },
  thumbItem: {
    alignItems: 'center',
    padding: 4,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  thumbItemActive: {
    borderColor: '#7B2CBF',
    backgroundColor: '#F8F4FC',
  },
  miniThumb: {
    width: 48,
    height: 48,
    borderRadius: 6,
    backgroundColor: '#EEE',
  },
  thumbLabel: {
    fontSize: 10,
    color: '#888',
    marginTop: 2,
    fontWeight: '600',
  },
  thumbLabelActive: {
    color: '#7B2CBF',
  },
  singleLabel: {
    fontSize: 11,
    color: '#999',
    marginTop: 6,
    fontWeight: '600',
  },
  selectHint: {
    fontSize: 11,
    color: '#7B2CBF',
    marginTop: 8,
    textAlign: 'center',
    fontWeight: '600',
  },
  precoBox: {
    marginTop: 10,
    alignItems: 'center',
    padding: 8,
    backgroundColor: '#F8F4FC',
    borderRadius: 8,
    width: '100%',
  },
  precoTotal: {
    fontSize: 18,
    fontWeight: '700',
    color: '#333',
  },
  precoSinal: {
    fontSize: 14,
    fontWeight: '600',
    color: '#7B2CBF',
    marginTop: 2,
  },
  precoDuracao: {
    fontSize: 12,
    color: '#888',
    marginTop: 4,
  },
});
