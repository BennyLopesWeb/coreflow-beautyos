/**
 * Seletor de comprovante de depósito (imagem ou PDF).
 */
import React, { useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  Platform,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { Ionicons } from '@expo/vector-icons';

export interface ComprovanteArquivo {
  /** URI local do arquivo (web ou mobile). */
  uri: string;
  /** Nome do arquivo para upload. */
  name: string;
  /** MIME type do arquivo. */
  type: string;
  /** Objeto File nativo no web (quando disponível). */
  file?: File;
}

interface ComprovantePickerProps {
  /** Arquivo selecionado ou null. */
  value: ComprovanteArquivo | null;
  /** Callback ao selecionar ou remover arquivo. */
  onChange: (arquivo: ComprovanteArquivo | null) => void;
}

/**
 * Permite anexar comprovante de depósito via galeria ou arquivo (web).
 *
 * @param {ComprovantePickerProps} props - Valor e callback de mudança.
 * @returns {JSX.Element} Área de seleção de comprovante.
 */
export const ComprovantePicker: React.FC<ComprovantePickerProps> = ({
  value,
  onChange,
}) => {
  const inputRef = useRef<HTMLInputElement | null>(null);

  /**
   * Abre seletor de imagem da galeria (mobile).
   */
  const escolherDaGaleria = async () => {
    const permissao = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permissao.granted) {
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: false,
      quality: 0.85,
    });

    if (result.canceled || !result.assets?.length) {
      return;
    }

    const asset = result.assets[0];
    const ext = asset.uri.split('.').pop()?.toLowerCase() || 'jpg';
    onChange({
      uri: asset.uri,
      name: `comprovante.${ext}`,
      type: asset.mimeType || 'image/jpeg',
    });
  };

  /**
   * Trata seleção de arquivo via input HTML (web).
   */
  const handleWebFile = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    const uri = URL.createObjectURL(file);
    onChange({
      uri,
      name: file.name,
      type: file.type || 'application/octet-stream',
      file,
    });
  };

  const isPdf = value?.type === 'application/pdf';

  return (
    <View style={styles.container}>
      {Platform.OS === 'web' && (
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,application/pdf"
          style={{ display: 'none' }}
          onChange={handleWebFile}
        />
      )}

      {value ? (
        <View style={styles.previewBox}>
          {!isPdf ? (
            <Image source={{ uri: value.uri }} style={styles.previewImage} resizeMode="cover" />
          ) : (
            <View style={styles.pdfBox}>
              <Ionicons name="document-text" size={32} color="#7B2CBF" />
              <Text style={styles.pdfName} numberOfLines={1}>
                {value.name}
              </Text>
            </View>
          )}
          <View style={styles.previewActions}>
            <TouchableOpacity
              style={styles.changeBtn}
              onPress={() => {
                onChange(null);
                if (Platform.OS === 'web') {
                  inputRef.current?.click();
                } else {
                  escolherDaGaleria();
                }
              }}
            >
              <Text style={styles.changeBtnText}>Trocar</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.removeBtn} onPress={() => onChange(null)}>
              <Text style={styles.removeBtnText}>Remover</Text>
            </TouchableOpacity>
          </View>
        </View>
      ) : (
        <TouchableOpacity
          style={styles.uploadArea}
          onPress={() => {
            if (Platform.OS === 'web') {
              inputRef.current?.click();
            } else {
              escolherDaGaleria();
            }
          }}
        >
          <Ionicons name="cloud-upload-outline" size={28} color="#7B2CBF" />
          <Text style={styles.uploadTitle}>Anexar comprovante</Text>
          <Text style={styles.uploadHint}>JPG, PNG, WEBP ou PDF — máx. 5 MB</Text>
        </TouchableOpacity>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginTop: 4,
  },
  uploadArea: {
    borderWidth: 2,
    borderColor: '#DDD',
    borderStyle: 'dashed',
    borderRadius: 10,
    padding: 20,
    alignItems: 'center',
    backgroundColor: '#FAFAFA',
  },
  uploadTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: '#333',
    marginTop: 8,
  },
  uploadHint: {
    fontSize: 12,
    color: '#999',
    marginTop: 4,
    textAlign: 'center',
  },
  previewBox: {
    borderRadius: 10,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#EEE',
    backgroundColor: '#FFF',
  },
  previewImage: {
    width: '100%',
    height: 160,
    backgroundColor: '#F0F0F0',
  },
  pdfBox: {
    height: 100,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F8F4FC',
    padding: 12,
  },
  pdfName: {
    marginTop: 6,
    fontSize: 13,
    color: '#555',
    maxWidth: '90%',
  },
  previewActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 8,
    padding: 10,
  },
  changeBtn: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    backgroundColor: '#EEE',
  },
  changeBtnText: {
    fontSize: 13,
    color: '#333',
    fontWeight: '600',
  },
  removeBtn: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    backgroundColor: '#FEE',
  },
  removeBtnText: {
    fontSize: 13,
    color: '#C0392B',
    fontWeight: '600',
  },
});
