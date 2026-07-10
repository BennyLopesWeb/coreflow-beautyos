/**
 * Componente Loader
 * Exibe indicador de carregamento
 */
import React from 'react';
import { View, ActivityIndicator, StyleSheet, Text } from 'react-native';

interface LoaderProps {
  message?: string;
  size?: 'small' | 'large';
}

export const Loader: React.FC<LoaderProps> = ({ message, size = 'large' }) => {
  return (
    <View style={styles.container}>
      <ActivityIndicator size={size} color="#7B2CBF" />
      {message && <Text style={styles.message}>{message}</Text>}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  message: {
    marginTop: 16,
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
  },
});

