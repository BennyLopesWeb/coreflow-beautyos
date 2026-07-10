/**
 * Componente CardTranca
 * Card de categoria — preços ficam nos modelos individuais.
 */
import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Tranca } from '../types';
import { TrancaThumbnail } from './TrancaThumbnail';

interface CardTrancaProps {
  /** Dados da categoria de trança. */
  tranca: Tranca;
  /** Callback ao pressionar o card. */
  onPress: () => void;
}

/**
 * Card de catálogo listando categoria (modelos têm preço individual).
 *
 * @param {CardTrancaProps} props - Trança e handler de clique.
 * @returns {JSX.Element} Card clicável da categoria.
 */
export const CardTranca: React.FC<CardTrancaProps> = ({ tranca, onPress }) => {
  const fotos = tranca.imagens?.filter(Boolean) ?? [];
  const imagem = fotos[0] ?? null;
  const qtdModelos = fotos.length;

  return (
    <View style={styles.card}>
      <View style={styles.row}>
        {imagem ? (
          <View style={styles.thumbWrap}>
            <TrancaThumbnail
              uri={imagem}
              size={100}
              alt={tranca.nome}
              onPress={onPress}
            />
            {qtdModelos > 1 && (
              <View style={styles.fotoBadge}>
                <Text style={styles.fotoBadgeText}>{qtdModelos} modelos</Text>
              </View>
            )}
          </View>
        ) : (
          <TouchableOpacity style={styles.placeholder} onPress={onPress} activeOpacity={0.7}>
            <Text style={styles.placeholderText}>Sem foto</Text>
          </TouchableOpacity>
        )}

        <TouchableOpacity style={styles.content} onPress={onPress} activeOpacity={0.7}>
          <Text style={styles.title} numberOfLines={1}>
            {tranca.nome}
          </Text>
          {tranca.descricao ? (
            <Text style={styles.description} numberOfLines={3}>
              {tranca.descricao}
            </Text>
          ) : null}

          <View style={styles.footer}>
            <Text style={styles.cta}>
              {qtdModelos > 0
                ? `${qtdModelos} modelo${qtdModelos > 1 ? 's' : ''} — ver preços`
                : 'Ver modelos'}
            </Text>
          </View>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const THUMB = 100;

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    marginBottom: 12,
    padding: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 3,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  thumbWrap: {
    position: 'relative',
  },
  placeholder: {
    width: THUMB,
    height: THUMB,
    borderRadius: 10,
    backgroundColor: '#EEE',
    justifyContent: 'center',
    alignItems: 'center',
  },
  placeholderText: {
    fontSize: 11,
    color: '#999',
  },
  content: {
    flex: 1,
    minWidth: 0,
  },
  title: {
    fontSize: 17,
    fontWeight: '700',
    color: '#333',
    marginBottom: 4,
  },
  description: {
    fontSize: 13,
    color: '#666',
    lineHeight: 18,
    marginBottom: 10,
  },
  footer: {
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#F0F0F0',
  },
  cta: {
    fontSize: 14,
    fontWeight: '700',
    color: '#7B2CBF',
  },
  fotoBadge: {
    position: 'absolute',
    bottom: 4,
    left: 4,
    backgroundColor: 'rgba(123,44,191,0.9)',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  fotoBadgeText: {
    color: '#FFF',
    fontSize: 10,
    fontWeight: '700',
  },
});
