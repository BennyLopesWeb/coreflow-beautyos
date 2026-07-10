import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';

interface TimeSlotProps {
  horario: string;
  disponivel: boolean;
  selected?: boolean;
  onPress: () => void;
}

export const TimeSlot: React.FC<TimeSlotProps> = ({
  horario,
  disponivel,
  selected = false,
  onPress,
}) => {
  return (
    <TouchableOpacity
      style={[
        styles.slot,
        selected && styles.slotSelected,
        !disponivel && styles.slotDisabled,
      ]}
      onPress={onPress}
      disabled={!disponivel}
    >
      <Text style={[styles.text, selected && styles.textSelected]}>
        {horario}
      </Text>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  slot: {
    padding: 16,
    borderRadius: 8,
    backgroundColor: '#F0F0F0',
    margin: 4,
    minWidth: 100,
    alignItems: 'center',
  },
  slotSelected: {
    backgroundColor: '#7B2CBF',
  },
  slotDisabled: {
    opacity: 0.3,
    backgroundColor: '#E0E0E0',
  },
  text: {
    fontSize: 16,
    color: '#333',
    fontWeight: '500',
  },
  textSelected: {
    color: '#FFF',
    fontWeight: '700',
  },
});

