import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';

interface CalendarPickerProps {
  selectedDate: Date | null;
  onSelectDate: (date: Date) => void;
  disabledDates?: Date[];
  minDate?: Date;
  maxDate?: Date;
}

export const CalendarPicker: React.FC<CalendarPickerProps> = ({
  selectedDate,
  onSelectDate,
  disabledDates = [],
  minDate,
  maxDate,
}) => {
  const today = new Date();
  const dates: Date[] = [];
  
  // Gera próximos 30 dias
  for (let i = 0; i < 30; i++) {
    const date = new Date(today);
    date.setDate(today.getDate() + i);
    dates.push(date);
  }

  const isDisabled = (date: Date) => {
    if (minDate && date < minDate) return true;
    if (maxDate && date > maxDate) return true;
    return disabledDates.some(d => d.toDateString() === date.toDateString());
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('pt-BR', { weekday: 'short', day: 'numeric', month: 'short' });
  };

  return (
    <View style={styles.container}>
      {dates.map((date, index) => {
        const disabled = isDisabled(date);
        const selected = selectedDate?.toDateString() === date.toDateString();
        
        return (
          <TouchableOpacity
            key={index}
            style={[
              styles.dateButton,
              selected && styles.dateButtonSelected,
              disabled && styles.dateButtonDisabled,
            ]}
            onPress={() => !disabled && onSelectDate(date)}
            disabled={disabled}
          >
            <Text style={[styles.dateText, selected && styles.dateTextSelected]}>
              {formatDate(date)}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  dateButton: {
    padding: 12,
    borderRadius: 8,
    backgroundColor: '#F0F0F0',
    minWidth: 100,
    alignItems: 'center',
  },
  dateButtonSelected: {
    backgroundColor: '#7B2CBF',
  },
  dateButtonDisabled: {
    opacity: 0.3,
  },
  dateText: {
    fontSize: 12,
    color: '#333',
  },
  dateTextSelected: {
    color: '#FFF',
    fontWeight: '600',
  },
});

