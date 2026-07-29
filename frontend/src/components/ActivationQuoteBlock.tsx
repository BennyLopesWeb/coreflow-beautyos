/**
 * Exibe sinal comercial e mínimo de ativação com rótulos distintos.
 */
import React from 'react';
import { View, Text, StyleSheet, StyleProp, TextStyle, ViewStyle } from 'react-native';
import { formatarMoeda, labelPercentualSinal } from '../utils/trancaFormat';
import { resolveMinimumActivationLabel } from '../utils/money';

export interface ActivationQuoteBlockProps {
  /** Cotação comercial do sinal (deposit_amount / valor_sinal). */
  sinalSugerido?: string | number | null;
  /** Percentual comercial opcional (fração 0–1) só para rótulo do sinal. */
  percentualSinal?: string | number;
  /** Mínimo em reais vindo do backend. */
  minimumActivationAmount?: string | number | null;
  /** Mínimo em centavos vindo do backend. */
  minimumActivationCents?: number | null;
  /** Estilo do container. */
  style?: StyleProp<ViewStyle>;
  /** Estilo do texto. */
  textStyle?: StyleProp<TextStyle>;
  /** Se true, omite o sinal quando inválido/zero. */
  hideEmptySinal?: boolean;
}

/**
 * Bloco de cotação: sinal sugerido ≠ mínimo de ativação.
 *
 * Não calcula mínimo localmente. Só exibe mínimo se o backend enviar campos.
 *
 * @param props - Valores comerciais e de ativação.
 * @returns JSX com linhas de preço ou null se nada a exibir.
 */
export const ActivationQuoteBlock: React.FC<ActivationQuoteBlockProps> = ({
  sinalSugerido,
  percentualSinal,
  minimumActivationAmount,
  minimumActivationCents,
  style,
  textStyle,
  hideEmptySinal = false,
}) => {
  const sinalNum =
    sinalSugerido == null || sinalSugerido === ''
      ? NaN
      : Number.parseFloat(String(sinalSugerido).replace(',', '.'));
  const showSinal = Number.isFinite(sinalNum) && !(hideEmptySinal && sinalNum <= 0);
  const minimo = resolveMinimumActivationLabel(
    minimumActivationAmount,
    minimumActivationCents,
  );

  if (!showSinal && !minimo) {
    return null;
  }

  return (
    <View style={[styles.wrap, style]}>
      {showSinal ? (
        <Text style={[styles.line, textStyle]}>
          Sinal sugerido
          {percentualSinal != null
            ? ` (${labelPercentualSinal(percentualSinal)})`
            : ''}
          : {formatarMoeda(sinalSugerido as string | number)}
        </Text>
      ) : null}
      {minimo ? (
        <Text style={[styles.line, styles.minimo, textStyle]}>
          Mínimo para ativar a reserva: {minimo}
        </Text>
      ) : null}
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: {
    gap: 4,
  },
  line: {
    fontSize: 14,
    color: '#444',
  },
  minimo: {
    fontWeight: '600',
    color: '#5A189A',
  },
});
