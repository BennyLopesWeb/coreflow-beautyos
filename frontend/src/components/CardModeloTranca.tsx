/**
 * Card de modelo individual dentro de uma categoria de trança.
 */
import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Platform } from 'react-native';
import { TrancaImagem } from '../types';
import { TrancaThumbnail } from './TrancaThumbnail';
import { ButtonPrimary } from './ButtonPrimary';
import { formatarMoeda, formatarDuracao, labelPercentualSinal } from '../utils/trancaFormat';

interface CardModeloTrancaProps {
  /** Dados do modelo (foto com preço individual). */
  modelo: TrancaImagem;
  /** Nome da categoria (alt da imagem). */
  categoriaNome: string;
  /** Ao pressionar o card (ver detalhes). */
  onPress?: () => void;
  /** Ao pressionar Reservar. */
  onReservar: () => void;
}

/**
 * Exibe foto, nome, preço e botão Reservar de um modelo de trança.
 * O botão fica fora da área clicável do card para evitar conflito no web.
 *
 * @param {CardModeloTrancaProps} props - Modelo, categoria e callbacks.
 * @returns {JSX.Element} Card do modelo.
 */
export const CardModeloTranca: React.FC<CardModeloTrancaProps> = ({
  modelo,
  categoriaNome,
  onPress,
  onReservar,
}) => {
  const infoBlock = (
    <>
      <TrancaThumbnail uri={modelo.url} size={110} alt={`${categoriaNome} — ${modelo.nome}`} />
      <View style={styles.info}>
        <Text style={styles.nome} numberOfLines={2}>
          {modelo.nome}
        </Text>
        {modelo.descricao ? (
          <Text style={styles.descricao} numberOfLines={2}>
            {modelo.descricao}
          </Text>
        ) : null}
        {modelo.nivel_complexidade ? (
          <Text style={styles.complexidade}>
            Complexidade: {modelo.nivel_complexidade}
          </Text>
        ) : null}
        <Text style={styles.preco}>{formatarMoeda(modelo.valor_total)}</Text>
        {modelo.duracao_minutos > 0 && (
          <Text style={styles.duracao}>{formatarDuracao(modelo.duracao_minutos)}</Text>
        )}
        {parseFloat(modelo.valor_sinal) > 0 && (
          <Text style={styles.sinal}>
            Sinal {labelPercentualSinal(modelo.percentual_sinal)}: {formatarMoeda(modelo.valor_sinal)}
          </Text>
        )}
      </View>
    </>
  );

  return (
    <View style={styles.card}>
      {onPress ? (
        <TouchableOpacity
          style={[styles.topRow, Platform.OS === 'web' && styles.webClickable]}
          onPress={onPress}
          activeOpacity={0.85}
          accessibilityRole="button"
        >
          {infoBlock}
        </TouchableOpacity>
      ) : (
        <View style={styles.topRow}>{infoBlock}</View>
      )}
      <View style={styles.btnWrap}>
        <ButtonPrimary title="Reservar" onPress={onReservar} />
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 12,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 3,
  },
  topRow: {
    flexDirection: 'row',
    gap: 12,
  },
  webClickable: {
    cursor: 'pointer',
  } as object,
  info: {
    flex: 1,
    minWidth: 0,
  },
  nome: {
    fontSize: 17,
    fontWeight: '700',
    color: '#333',
    marginBottom: 4,
  },
  descricao: {
    fontSize: 13,
    color: '#666',
    lineHeight: 18,
    marginBottom: 4,
  },
  complexidade: {
    fontSize: 11,
    color: '#999',
    marginBottom: 4,
    textTransform: 'capitalize',
  },
  preco: {
    fontSize: 20,
    fontWeight: '800',
    color: '#7B2CBF',
    marginTop: 8,
  },
  duracao: {
    fontSize: 13,
    color: '#666',
    marginTop: 4,
  },
  sinal: {
    fontSize: 13,
    color: '#7B2CBF',
    fontWeight: '600',
    marginTop: 2,
  },
  btnWrap: {
    marginTop: 12,
  },
});
