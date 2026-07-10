/**
 * Alertas compatíveis com web e mobile.
 */
import { Alert, Platform } from 'react-native';

/**
 * Exibe alerta nativo no mobile ou `window.alert` no web.
 *
 * @param title - Título do alerta.
 * @param message - Mensagem exibida ao usuário.
 * @param onOk - Callback opcional após fechar (útil no mobile).
 */
export function showAlert(title: string, message: string, onOk?: () => void): void {
  if (Platform.OS === 'web') {
    window.alert(`${title}\n\n${message}`);
    onOk?.();
    return;
  }
  if (onOk) {
    Alert.alert(title, message, [{ text: 'OK', onPress: onOk }]);
    return;
  }
  Alert.alert(title, message);
}
