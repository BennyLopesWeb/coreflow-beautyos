/**
 * Componente ButtonPrimary
 * Botão primário reutilizável (compatível web e mobile).
 */
import React from 'react';
import {
  Pressable,
  Text,
  StyleSheet,
  ActivityIndicator,
  Platform,
  GestureResponderEvent,
} from 'react-native';

interface ButtonPrimaryProps {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
  variant?: 'primary' | 'secondary' | 'danger';
}

export const ButtonPrimary: React.FC<ButtonPrimaryProps> = ({
  title,
  onPress,
  disabled = false,
  loading = false,
  variant = 'primary',
}) => {
  const handlePress = (e: GestureResponderEvent) => {
    if (Platform.OS === 'web') {
      e.stopPropagation?.();
    }
    if (!disabled && !loading) {
      onPress();
    }
  };

  return (
    <Pressable
      style={({ pressed }) => [
        styles.button,
        variant === 'secondary' && styles.buttonSecondary,
        variant === 'danger' && styles.buttonDanger,
        (disabled || loading) && styles.buttonDisabled,
        Platform.OS === 'web' && styles.webButton,
        pressed && !disabled && !loading && styles.buttonPressed,
      ]}
      onPress={handlePress}
      disabled={disabled || loading}
      accessibilityRole="button"
    >
      {loading ? (
        <ActivityIndicator color="#FFF" />
      ) : (
        <Text style={styles.text}>{title}</Text>
      )}
    </Pressable>
  );
};

const styles = StyleSheet.create({
  button: {
    backgroundColor: '#7B2CBF',
    paddingVertical: 16,
    paddingHorizontal: 24,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 52,
  },
  buttonSecondary: {
    backgroundColor: '#6C757D',
  },
  buttonDanger: {
    backgroundColor: '#DC3545',
  },
  buttonDisabled: {
    backgroundColor: '#CCC',
    opacity: 0.6,
  },
  text: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '600',
  },
  webButton: {
    cursor: 'pointer',
    userSelect: 'none',
  } as object,
  buttonPressed: {
    opacity: 0.85,
  },
});

