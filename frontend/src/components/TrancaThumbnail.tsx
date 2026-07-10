/**
 * Miniatura de imagem da trança.
 * No catálogo abre detalhes; na tela de detalhes pode ampliar em modal.
 */
import React, { useState } from 'react';
import {
  View,
  Image,
  StyleSheet,
  TouchableOpacity,
  Modal,
  Text,
  Platform,
  Dimensions,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface TrancaThumbnailProps {
  /** URL da imagem da trança. */
  uri: string;
  /** Largura da miniatura em pixels. */
  size?: number;
  /** Texto alternativo / legenda no modal. */
  alt?: string;
  /**
   * Ação ao tocar (ex.: abrir detalhes).
   * Se informado, substitui a ampliação em modal.
   */
  onPress?: () => void;
  /**
   * Permite ampliar a foto em modal ao tocar.
   * Ignorado quando `onPress` está definido.
   */
  enableZoom?: boolean;
}

const { width: SCREEN_W, height: SCREEN_H } = Dimensions.get('window');
const MODAL_IMG_W = Math.min(SCREEN_W - 32, 560);
const MODAL_IMG_H = Math.min(SCREEN_H * 0.72, 640);

/**
 * Renderiza imagem ampliada com fallback nativo no web.
 */
function ImagemAmpliada({ uri, alt }: { uri: string; alt: string }) {
  if (Platform.OS === 'web') {
    return (
      <img
        src={uri}
        alt={alt}
        style={{
          width: MODAL_IMG_W,
          height: MODAL_IMG_H,
          objectFit: 'contain',
          borderRadius: 8,
          display: 'block',
          backgroundColor: '#111',
        }}
      />
    );
  }

  return (
    <Image
      source={{ uri }}
      style={styles.modalImage}
      resizeMode="contain"
      accessibilityLabel={alt}
    />
  );
}

/**
 * Exibe foto pequena; toque abre detalhes ou amplia conforme configuração.
 *
 * @param {TrancaThumbnailProps} props - URI, tamanho, onPress ou zoom.
 * @returns {JSX.Element} Miniatura clicável.
 */
export const TrancaThumbnail: React.FC<TrancaThumbnailProps> = ({
  uri,
  size = 96,
  alt = 'Foto da trança',
  onPress,
  enableZoom = true,
}) => {
  const [ampliada, setAmpliada] = useState(false);

  const handlePress = () => {
    if (onPress) {
      onPress();
      return;
    }
    if (enableZoom) {
      setAmpliada(true);
    }
  };

  const showHint = onPress || enableZoom;

  return (
    <>
      <TouchableOpacity
        style={[styles.thumbWrap, { width: size, height: size }]}
        onPress={handlePress}
        activeOpacity={0.85}
        accessibilityLabel={onPress ? `Ver detalhes de ${alt}` : `Ampliar ${alt}`}
      >
        <Image source={{ uri }} style={styles.thumbImage} resizeMode="cover" />
        {showHint && (
          <View style={styles.hintBadge}>
            <Ionicons
              name={onPress ? 'chevron-forward' : 'expand-outline'}
              size={14}
              color="#FFF"
            />
          </View>
        )}
      </TouchableOpacity>

      {!onPress && enableZoom && (
        <Modal
          visible={ampliada}
          transparent
          animationType="fade"
          onRequestClose={() => setAmpliada(false)}
          statusBarTranslucent
        >
          <View style={styles.modalRoot}>
            <TouchableOpacity
              style={styles.modalBackdrop}
              activeOpacity={1}
              onPress={() => setAmpliada(false)}
            />
            <View style={styles.modalBox}>
              <ImagemAmpliada uri={uri} alt={alt} />
              {alt ? <Text style={styles.modalCaption}>{alt}</Text> : null}
              <TouchableOpacity
                style={styles.closeBtn}
                onPress={() => setAmpliada(false)}
                accessibilityLabel="Fechar imagem"
              >
                <Ionicons name="close-circle" size={36} color="#FFF" />
              </TouchableOpacity>
            </View>
          </View>
        </Modal>
      )}
    </>
  );
};

const styles = StyleSheet.create({
  thumbWrap: {
    borderRadius: 10,
    overflow: 'hidden',
    backgroundColor: '#EEE',
    position: 'relative',
  },
  thumbImage: {
    width: '100%',
    height: '100%',
  },
  hintBadge: {
    position: 'absolute',
    bottom: 4,
    right: 4,
    backgroundColor: 'rgba(0,0,0,0.45)',
    borderRadius: 4,
    padding: 2,
  },
  modalRoot: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalBackdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.9)',
  },
  modalBox: {
    width: MODAL_IMG_W,
    maxWidth: '100%',
    alignItems: 'center',
    zIndex: 2,
    elevation: 10,
  },
  modalImage: {
    width: MODAL_IMG_W,
    height: MODAL_IMG_H,
    backgroundColor: '#111',
    borderRadius: 8,
  },
  modalCaption: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '600',
    marginTop: 12,
    textAlign: 'center',
    paddingHorizontal: 8,
  },
  closeBtn: {
    marginTop: 16,
    padding: 8,
  },
});
