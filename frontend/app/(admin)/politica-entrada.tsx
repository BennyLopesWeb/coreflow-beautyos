/**
 * Admin — política de entrada mínima (grupo activation).
 *
 * Consome ``/admin/booking-policy``. Não envia company_id.
 * Não calcula mínimos; apenas configura a política do tenant.
 */
import React, { useCallback, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { useFocusEffect } from 'expo-router';
import {
  bookingPolicyService,
  type ActivationModeV1,
  type ActivationPolicyV1,
  type BookingPolicyAdminResponseV1,
} from '../../src/services/bookingPolicyService';
import {
  parseApiError,
  resolvePolicyAdminSaveError,
  shouldRenderPolicyForm,
} from '../../src/utils/apiError';
import { formatCentsToBrl, parseMoneyToCents } from '../../src/utils/money';
import { showAlert } from '../../src/utils/alert';

type FormMode = ActivationModeV1;

/**
 * Tela administrativa do grupo ``activation``.
 *
 * @returns JSX da configuração de entrada.
 */
export default function PoliticaEntradaScreen() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [forbidden, setForbidden] = useState(false);
  const [policy, setPolicy] = useState<BookingPolicyAdminResponseV1 | null>(null);
  const [mode, setMode] = useState<FormMode>('percentage_with_cap');
  const [percentage, setPercentage] = useState('20');
  const [capReais, setCapReais] = useState('100,00');
  const [standardPct, setStandardPct] = useState('20');
  const [highThresholdReais, setHighThresholdReais] = useState('500,00');
  const [highPct, setHighPct] = useState('30');
  const [tieredCapReais, setTieredCapReais] = useState('');
  const [reason, setReason] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  /** Rascunho local após 409 — não sobrescreve o remoto automaticamente. */
  const [conflictNotice, setConflictNotice] = useState<string | null>(null);

  /**
   * Preenche o formulário a partir da política carregada.
   *
   * @param data - Resposta GET/PATCH.
   */
  const applyPolicyToForm = (data: BookingPolicyAdminResponseV1) => {
    setPolicy(data);
    const act = data.policy?.activation;
    if (!act) {
      setMode('percentage_with_cap');
      setPercentage('20');
      setCapReais('100,00');
      return;
    }
    if (act.mode === 'tiered_percentage') {
      setMode('tiered_percentage');
      setStandardPct(String(act.standard_percentage ?? 20));
      setHighPct(String(act.high_value_percentage ?? 30));
      setHighThresholdReais(
        act.high_value_threshold_cents != null
          ? formatCentsToBrl(act.high_value_threshold_cents).replace('R$ ', '')
          : '500,00',
      );
      setTieredCapReais(
        act.cap_cents != null
          ? formatCentsToBrl(act.cap_cents).replace('R$ ', '')
          : '',
      );
      setPercentage('');
      setCapReais('');
    } else {
      setMode('percentage_with_cap');
      setPercentage(String(act.percentage ?? 20));
      setCapReais(
        act.cap_cents != null
          ? formatCentsToBrl(act.cap_cents).replace('R$ ', '')
          : '100,00',
      );
      setStandardPct('');
      setHighPct('');
      setHighThresholdReais('');
      setTieredCapReais('');
    }
  };

  /**
   * Carrega GET /admin/booking-policy.
   *
   * @param opts.clearReason - Se true, limpa o motivo após reload de conflito.
   */
  const load = async (opts?: { clearReason?: boolean }) => {
    setLoading(true);
    setForbidden(false);
    setFieldErrors({});
    try {
      const data = await bookingPolicyService.obter();
      applyPolicyToForm(data);
      if (opts?.clearReason) {
        setReason('');
      }
    } catch (e: unknown) {
      const parsed = parseApiError(e, 'Erro ao carregar política');
      if (parsed.status === 403) {
        setForbidden(true);
        setPolicy(null);
      } else {
        showAlert('Erro', parsed.message);
      }
    } finally {
      setLoading(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      load();
    }, []),
  );

  /**
   * Troca o modo e limpa campos do modo anterior (evita payload híbrido).
   *
   * @param next - Novo modo.
   */
  const changeMode = (next: FormMode) => {
    setMode(next);
    setFieldErrors({});
    setConflictNotice(null);
    if (next === 'percentage_with_cap') {
      setPercentage((p) => p || '20');
      setCapReais((c) => c || '100,00');
      setStandardPct('');
      setHighPct('');
      setHighThresholdReais('');
      setTieredCapReais('');
    } else {
      setStandardPct((p) => p || '20');
      setHighPct((p) => p || '30');
      setHighThresholdReais((t) => t || '500,00');
      setPercentage('');
      setCapReais('');
    }
  };

  /**
   * Monta o objeto activation sem campos do outro modo.
   *
   * @returns Activation tipada ou null se validação local falhar.
   */
  const buildActivation = (): ActivationPolicyV1 | null => {
    const errors: Record<string, string> = {};
    if (mode === 'percentage_with_cap') {
      const pct = Number.parseInt(percentage, 10);
      const cap = parseMoneyToCents(capReais);
      if (!Number.isInteger(pct) || pct < 0 || pct > 100) {
        errors['activation.percentage'] = 'Percentual inteiro de 0 a 100';
      }
      if (cap == null) {
        errors['activation.cap_cents'] = 'Teto inválido';
      }
      setFieldErrors(errors);
      if (Object.keys(errors).length) {
        return null;
      }
      return {
        mode: 'percentage_with_cap',
        currency: 'BRL',
        percentage: pct,
        cap_cents: cap!,
      };
    }

    const std = Number.parseInt(standardPct, 10);
    const high = Number.parseInt(highPct, 10);
    const threshold = parseMoneyToCents(highThresholdReais);
    let cap: number | null | undefined;
    if (tieredCapReais.trim()) {
      cap = parseMoneyToCents(tieredCapReais);
      if (cap == null) {
        errors['activation.cap_cents'] = 'Teto opcional inválido';
      }
    } else {
      cap = null;
    }
    if (!Number.isInteger(std) || std < 0 || std > 100) {
      errors['activation.standard_percentage'] = 'Percentual padrão 0–100';
    }
    if (!Number.isInteger(high) || high < 0 || high > 100) {
      errors['activation.high_value_percentage'] = 'Percentual alto 0–100';
    }
    if (threshold == null || threshold <= 0) {
      errors['activation.high_value_threshold_cents'] = 'Limite de alto valor inválido';
    }
    if (
      Number.isInteger(std) &&
      Number.isInteger(high) &&
      high < std
    ) {
      errors['activation.high_value_percentage'] =
        'Deve ser >= percentual padrão';
    }
    setFieldErrors(errors);
    if (Object.keys(errors).length) {
      return null;
    }
    return {
      mode: 'tiered_percentage',
      currency: 'BRL',
      standard_percentage: std,
      high_value_threshold_cents: threshold!,
      high_value_percentage: high,
      cap_cents: cap ?? null,
    };
  };

  /**
   * Persiste via PATCH com reason e expected_version.
   */
  const salvar = async () => {
    setConflictNotice(null);
    if (!reason.trim()) {
      setFieldErrors({ reason: 'Motivo obrigatório' });
      showAlert('Motivo obrigatório', 'Informe o motivo da alteração para auditoria.');
      return;
    }
    const activation = buildActivation();
    if (!activation) {
      showAlert('Dados inválidos', 'Corrija os campos destacados.');
      return;
    }

    setSaving(true);
    setFieldErrors({});
    try {
      const body = {
        activation,
        reason: reason.trim(),
        ...(policy?.version != null
          ? { expected_version: policy.version }
          : {}),
      };
      const updated = await bookingPolicyService.atualizarActivation(body);
      applyPolicyToForm(updated);
      setReason('');
      showAlert('Sucesso', 'Política de entrada atualizada.');
    } catch (e: unknown) {
      const action = resolvePolicyAdminSaveError(e);
      if (action.kind === 'forbidden') {
        setForbidden(true);
        showAlert('Sem permissão', action.message);
        return;
      }
      if (action.kind === 'conflict_reload') {
        // Não sobrescreve o remoto com o draft local: GET redefine o form.
        setConflictNotice(
          'A política foi alterada por outro administrador. Recarregamos a versão atual. Revise os valores, informe um novo motivo e salve novamente.',
        );
        await load({ clearReason: true });
        showAlert('Conflito de versão', action.message);
        return;
      }
      if (action.kind === 'validation') {
        setFieldErrors(action.fieldErrors);
        showAlert('Validação', action.message);
        return;
      }
      showAlert('Erro', action.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color="#7B2CBF" />
        <Text style={styles.muted}>Carregando política…</Text>
      </View>
    );
  }

  if (!shouldRenderPolicyForm({ forbidden, loading: false })) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorTitle}>Sem permissão</Text>
        <Text style={styles.muted}>
          Seu usuário não pode administrar a política de entrada deste tenant.
          A autorização final é definida pelo backend.
        </Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Política de entrada</Text>
      <Text style={styles.subtitle}>
        Define o mínimo financeiro para ativar reservas. O cálculo é feito só no
        servidor; esta tela apenas configura a política.
      </Text>

      <View style={styles.metaBox}>
        <Text style={styles.meta}>
          Origem: {policy?.source ?? '—'}
          {policy?.has_active_override ? ' (override ativo)' : ''}
        </Text>
        <Text style={styles.meta}>
          Versão: {policy?.version != null ? policy.version : 'sem override'}
        </Text>
        <Text style={styles.meta}>Moeda: BRL</Text>
      </View>

      {conflictNotice ? (
        <View style={styles.conflictBox}>
          <Text style={styles.conflictText}>{conflictNotice}</Text>
        </View>
      ) : null}

      <Text style={styles.label}>Modo</Text>
      <View style={styles.modeRow}>
        <TouchableOpacity
          style={[styles.modeBtn, mode === 'percentage_with_cap' && styles.modeBtnActive]}
          onPress={() => changeMode('percentage_with_cap')}
        >
          <Text
            style={[
              styles.modeBtnText,
              mode === 'percentage_with_cap' && styles.modeBtnTextActive,
            ]}
          >
            % com teto
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.modeBtn, mode === 'tiered_percentage' && styles.modeBtnActive]}
          onPress={() => changeMode('tiered_percentage')}
        >
          <Text
            style={[
              styles.modeBtnText,
              mode === 'tiered_percentage' && styles.modeBtnTextActive,
            ]}
          >
            Por faixas
          </Text>
        </TouchableOpacity>
      </View>

      {mode === 'percentage_with_cap' ? (
        <>
          <Text style={styles.label}>Percentual (0–100)</Text>
          <TextInput
            style={styles.input}
            keyboardType="number-pad"
            value={percentage}
            onChangeText={setPercentage}
          />
          {fieldErrors['activation.percentage'] ? (
            <Text style={styles.fieldError}>{fieldErrors['activation.percentage']}</Text>
          ) : null}
          <Text style={styles.label}>Teto (R$)</Text>
          <TextInput
            style={styles.input}
            keyboardType="decimal-pad"
            value={capReais}
            onChangeText={setCapReais}
            placeholder="100,00"
          />
          {fieldErrors['activation.cap_cents'] ? (
            <Text style={styles.fieldError}>{fieldErrors['activation.cap_cents']}</Text>
          ) : null}
        </>
      ) : (
        <>
          <Text style={styles.label}>Percentual padrão (0–100)</Text>
          <TextInput
            style={styles.input}
            keyboardType="number-pad"
            value={standardPct}
            onChangeText={setStandardPct}
          />
          {fieldErrors['activation.standard_percentage'] ? (
            <Text style={styles.fieldError}>
              {fieldErrors['activation.standard_percentage']}
            </Text>
          ) : null}
          <Text style={styles.label}>Limite de alto valor (R$)</Text>
          <TextInput
            style={styles.input}
            keyboardType="decimal-pad"
            value={highThresholdReais}
            onChangeText={setHighThresholdReais}
            placeholder="500,00"
          />
          {fieldErrors['activation.high_value_threshold_cents'] ? (
            <Text style={styles.fieldError}>
              {fieldErrors['activation.high_value_threshold_cents']}
            </Text>
          ) : null}
          <Text style={styles.label}>Percentual de alto valor (0–100)</Text>
          <TextInput
            style={styles.input}
            keyboardType="number-pad"
            value={highPct}
            onChangeText={setHighPct}
          />
          {fieldErrors['activation.high_value_percentage'] ? (
            <Text style={styles.fieldError}>
              {fieldErrors['activation.high_value_percentage']}
            </Text>
          ) : null}
          <Text style={styles.label}>Teto opcional (R$)</Text>
          <TextInput
            style={styles.input}
            keyboardType="decimal-pad"
            value={tieredCapReais}
            onChangeText={setTieredCapReais}
            placeholder="vazio = sem teto"
          />
          {fieldErrors['activation.cap_cents'] ? (
            <Text style={styles.fieldError}>{fieldErrors['activation.cap_cents']}</Text>
          ) : null}
        </>
      )}

      <Text style={styles.label}>Motivo da alteração *</Text>
      <TextInput
        style={[styles.input, styles.reason]}
        value={reason}
        onChangeText={setReason}
        placeholder="Ex.: ajuste de teto para alta temporada"
        multiline
      />
      {fieldErrors.reason ? (
        <Text style={styles.fieldError}>{fieldErrors.reason}</Text>
      ) : null}

      <TouchableOpacity
        style={[styles.saveBtn, saving && styles.saveBtnDisabled]}
        onPress={salvar}
        disabled={saving}
      >
        {saving ? (
          <ActivityIndicator color="#FFF" />
        ) : (
          <Text style={styles.saveBtnText}>Salvar política</Text>
        )}
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5' },
  content: { padding: 16, paddingBottom: 40 },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
    backgroundColor: '#F5F5F5',
  },
  title: { fontSize: 22, fontWeight: '700', color: '#222', marginBottom: 8 },
  subtitle: { fontSize: 14, color: '#666', marginBottom: 16, lineHeight: 20 },
  metaBox: {
    backgroundColor: '#FFF',
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#E0E0E0',
  },
  meta: { fontSize: 13, color: '#444', marginBottom: 4 },
  conflictBox: {
    backgroundColor: '#FFF3CD',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  conflictText: { color: '#856404', fontSize: 13, lineHeight: 18 },
  label: { fontSize: 13, fontWeight: '600', color: '#333', marginBottom: 6, marginTop: 10 },
  input: {
    backgroundColor: '#FFF',
    borderWidth: 1,
    borderColor: '#CCC',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
  },
  reason: { minHeight: 72, textAlignVertical: 'top' },
  modeRow: { flexDirection: 'row', gap: 8 },
  modeBtn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    backgroundColor: '#E9ECEF',
    alignItems: 'center',
  },
  modeBtnActive: { backgroundColor: '#7B2CBF' },
  modeBtnText: { color: '#333', fontWeight: '600' },
  modeBtnTextActive: { color: '#FFF' },
  fieldError: { color: '#C1121F', fontSize: 12, marginTop: 4 },
  saveBtn: {
    marginTop: 24,
    backgroundColor: '#7B2CBF',
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: 'center',
  },
  saveBtnDisabled: { opacity: 0.6 },
  saveBtnText: { color: '#FFF', fontWeight: '700', fontSize: 16 },
  muted: { color: '#666', textAlign: 'center', marginTop: 8, lineHeight: 20 },
  errorTitle: { fontSize: 18, fontWeight: '700', color: '#C1121F' },
});
