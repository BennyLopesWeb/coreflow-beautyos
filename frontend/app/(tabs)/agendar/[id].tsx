import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TextInput, TouchableOpacity } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { trancaService } from '../../../src/services/trancaService';
import { agendamentoService } from '../../../src/services/agendamentoService';
import { filaService } from '../../../src/services/filaService';
import { pagamentoService } from '../../../src/services/pagamentoService';
import { Tranca, TrancaImagem, HorarioDisponivel } from '../../../src/types';
import { ButtonPrimary } from '../../../src/components/ButtonPrimary';
import { Loader } from '../../../src/components/Loader';
import { CalendarPicker } from '../../../src/components/CalendarPicker';
import { TimeSlot } from '../../../src/components/TimeSlot';
import { ComprovantePicker, ComprovanteArquivo } from '../../../src/components/ComprovantePicker';
import { TrancaGaleria } from '../../../src/components/TrancaGaleria';
import { getApiErrorMessage } from '../../../src/utils/apiError';
import { showAlert } from '../../../src/utils/alert';
import { telefoneValido, telefonesIguais } from '../../../src/utils/telefone';
import { obterOuCriarCliente } from '../../../src/utils/clienteResolucao';
import { useAuth } from '../../../src/contexts/AuthContext';
import { formatLocalDateTime } from '../../../src/utils/datetime';
import { formatarMoeda, labelPercentualSinal } from '../../../src/utils/trancaFormat';

export default function AgendarScreen() {
  const { id, imagemId } = useLocalSearchParams<{ id: string; imagemId?: string }>();
  const router = useRouter();
  const { user } = useAuth();
  const telefoneCadastrado = user?.telefone?.trim() ?? '';
  const [tranca, setTranca] = useState<Tranca | null>(null);
  const [imagens, setImagens] = useState<TrancaImagem[]>([]);
  const [fotoSelecionada, setFotoSelecionada] = useState<TrancaImagem | null>(null);
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [horarios, setHorarios] = useState<HorarioDisponivel[]>([]);
  const [selectedHorario, setSelectedHorario] = useState<string | null>(null);
  const [nome, setNome] = useState('');
  const [telefone, setTelefone] = useState('');
  const [confirmarTelefone, setConfirmarTelefone] = useState('');
  const [email, setEmail] = useState('');
  const [comprovante, setComprovante] = useState<ComprovanteArquivo | null>(null);
  const [modoFila, setModoFila] = useState(false);
  const [observacoesFila, setObservacoesFila] = useState('');
  const [horarioDesejado, setHorarioDesejado] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (user) {
      setNome(user.nome ?? '');
      setEmail(user.email ?? '');
    }
  }, [user]);

  useEffect(() => {
    setLoading(true);
    setImagens([]);
    setFotoSelecionada(null);
    loadTranca();
  }, [id]);

  useEffect(() => {
    if (selectedDate) {
      loadHorarios();
    }
  }, [selectedDate, fotoSelecionada?.id]);

  /**
   * Carrega trança e galeria; pré-seleciona foto vinda da tela de detalhe.
   */
  const loadTranca = async () => {
    try {
      const trancaId = Number(id);
      const [data, fotos] = await Promise.all([
        trancaService.buscarPorId(trancaId),
        trancaService.listarImagens(trancaId),
      ]);
      setTranca(data);
      setImagens(fotos);

      const preferida = imagemId
        ? fotos.find((f) => f.id === Number(imagemId))
        : null;
      setFotoSelecionada(preferida ?? fotos[0] ?? null);
    } catch (error) {
      showAlert('Erro', 'Erro ao carregar trança');
      router.back();
    } finally {
      setLoading(false);
    }
  };

  const loadHorarios = async () => {
    if (!selectedDate || !tranca) return;

    try {
      const dataStr = selectedDate.toISOString().split('T')[0];
      const disponiveis = await agendamentoService.consultarDisponibilidade(
        dataStr,
        tranca.id,
        fotoSelecionada?.id,
      );
      setHorarios(disponiveis);
      const livres = disponiveis.filter((h) => h.disponivel);
      if (livres.length === 0) {
        setModoFila(true);
        setSelectedHorario(null);
      } else {
        setModoFila(false);
      }
    } catch (error) {
      console.error('Erro ao carregar horários:', error);
    }
  };

  /**
   * Retorna o telefone efetivo (cadastrado no perfil ou informado no formulário).
   */
  const telefoneEfetivo = (): string => telefoneCadastrado || telefone.trim();

  /**
   * Valida campos obrigatórios do cliente antes de reservar ou entrar na fila.
   *
   * @returns Mensagem de erro ou null se válido.
   */
  const validarDadosCliente = (): string | null => {
    if (!nome.trim()) {
      return 'Informe seu nome completo';
    }
    if (telefoneCadastrado) {
      if (!confirmarTelefone.trim()) {
        return 'Confirme seu telefone para continuar';
      }
      if (!telefonesIguais(telefoneCadastrado, confirmarTelefone)) {
        return 'O telefone de confirmação não confere com o cadastrado';
      }
    } else {
      if (!telefone.trim()) {
        return 'Informe seu telefone';
      }
      if (!telefoneValido(telefone)) {
        return 'Telefone inválido (mínimo 10 dígitos)';
      }
    }
    return null;
  };

  /**
   * Normaliza horário desejado para formato HH:MM:SS.
   */
  const formatarHorarioDesejado = (): string | undefined => {
    const bruto = horarioDesejado.trim();
    if (!bruto) return undefined;
    if (/^\d{1,2}:\d{2}$/.test(bruto)) {
      return `${bruto}:00`;
    }
    if (/^\d{1,2}:\d{2}:\d{2}$/.test(bruto)) {
      return bruto;
    }
    return undefined;
  };

  const handleEntrarFila = async (mesmoDia = false) => {
    const erroCliente = validarDadosCliente();
    if (erroCliente) {
      showAlert('Campos obrigatórios', erroCliente);
      return;
    }
    if (!selectedDate || !fotoSelecionada) {
      showAlert('Campos obrigatórios', 'Selecione a data do atendimento');
      return;
    }

    const horarioFmt = formatarHorarioDesejado();
    if (horarioDesejado.trim() && !horarioFmt) {
      showAlert('Horário inválido', 'Use o formato HH:MM (ex: 14:00)');
      return;
    }

    setSubmitting(true);
    try {
      const tel = telefoneEfetivo();
      const cliente = await obterOuCriarCliente(nome, tel, email);

      const dataStr = selectedDate.toISOString().split('T')[0];
      const item = await filaService.entrar({
        cliente_id: cliente.id,
        tranca_id: tranca!.id,
        service_image_id: fotoSelecionada.id,
        data_desejada: dataStr,
        horario_desejado: horarioFmt,
        observacoes: observacoesFila.trim() || undefined,
        mesmo_dia: mesmoDia || dataStr === new Date().toISOString().split('T')[0],
      });

      showAlert(
        'Entrada na fila confirmada',
        `Você entrou na fila na posição ${item.posicao}! A profissional entrará em contato para combinar o horário.`,
        () => router.replace('/(tabs)/fila'),
      );
    } catch (error: unknown) {
      showAlert('Falha ao entrar na fila', getApiErrorMessage(error, 'Não foi possível entrar na fila'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleAgendar = async () => {
    if (modoFila) {
      await handleEntrarFila(false);
      return;
    }

    const erroCliente = validarDadosCliente();
    if (erroCliente) {
      showAlert('Campos obrigatórios', erroCliente);
      return;
    }

    if (!selectedDate) {
      showAlert('Campos obrigatórios', 'Selecione a data do atendimento');
      return;
    }

    if (!selectedHorario) {
      showAlert('Campos obrigatórios', 'Selecione um horário disponível');
      return;
    }

    if (!fotoSelecionada) {
      showAlert('Campos obrigatórios', 'Selecione o modelo que deseja reservar');
      return;
    }

    setSubmitting(true);
    try {
      const tel = telefoneEfetivo();
      const cliente = await obterOuCriarCliente(nome, tel, email);

      const [hora, minuto] = selectedHorario.split(':');
      const dataHora = new Date(selectedDate);
      dataHora.setHours(Number(hora), Number(minuto), 0, 0);

      const agendamento = await agendamentoService.criar({
        cliente_id: cliente.id,
        tranca_id: tranca!.id,
        service_image_id: fotoSelecionada.id,
        data_hora: formatLocalDateTime(dataHora),
      });

      if (comprovante) {
        try {
          const res = await pagamentoService.enviarComprovante(agendamento.id, comprovante);
          showAlert('Comprovante enviado', res.mensagem);
        } catch (uploadError: unknown) {
          showAlert(
            'Aviso',
            getApiErrorMessage(
              uploadError,
              'Reserva criada, mas falhou ao enviar o comprovante.',
            ),
          );
        }
      }

      showAlert(
        'Reserva criada com sucesso',
        comprovante
          ? 'Comprovante recebido! Após confirmação do sinal, aguarde aprovação da profissional.'
          : 'Reserva criada! Pague o sinal e aguarde aprovação da profissional.',
        () => router.replace('/(tabs)/agendamentos'),
      );
    } catch (error: unknown) {
      showAlert('Falha na reserva', getApiErrorMessage(error, 'Erro ao criar agendamento'));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading || !tranca) {
    return <Loader message="Carregando..." />;
  }

  if (!fotoSelecionada) {
    return (
      <View style={styles.container}>
        <Text style={styles.erroModelo}>
          Selecione um modelo na categoria antes de agendar.
        </Text>
      </View>
    );
  }

  const horariosLivres = horarios.filter((h) => h.disponivel);

  const valorTotal = fotoSelecionada.valor_total;
  const valorSinal = fotoSelecionada.valor_sinal;
  const valorRestante =
    fotoSelecionada.valor_restante ??
    String(parseFloat(valorTotal) - parseFloat(valorSinal));

  return (
    <ScrollView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>Reservar {fotoSelecionada.nome}</Text>
        <Text style={styles.subtitle}>{tranca.nome}</Text>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Modelo selecionado</Text>
          <TrancaGaleria
            itens={[fotoSelecionada]}
            nome={tranca.nome}
            mainSize={120}
          />
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Selecione a data</Text>
          <CalendarPicker
            selectedDate={selectedDate}
            onSelectDate={setSelectedDate}
            minDate={new Date()}
          />
          <TouchableOpacity
            style={styles.hojeBtn}
            onPress={() => {
              const hoje = new Date();
              setSelectedDate(hoje);
              setModoFila(true);
            }}
          >
            <Text style={styles.hojeBtnText}>Preciso de atendimento hoje</Text>
          </TouchableOpacity>
        </View>

        {selectedDate && horariosLivres.length > 0 && !modoFila && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Selecione o horário</Text>
            <View style={styles.horarios}>
              {horariosLivres.map((h) => (
                <TimeSlot
                  key={h.horario}
                  horario={h.horario}
                  disponivel={h.disponivel}
                  selected={selectedHorario === h.horario}
                  onPress={() => setSelectedHorario(h.horario)}
                />
              ))}
            </View>
          </View>
        )}

        {selectedDate && (modoFila || horariosLivres.length === 0) && (
          <View style={styles.filaBox}>
            <Text style={styles.filaTitulo}>Não há horários disponíveis</Text>
            <Text style={styles.filaDesc}>
              Deseja entrar na fila de espera? A profissional avaliará a disponibilidade
              e entrará em contato para negociar o horário.
            </Text>
            <TextInput
              style={styles.input}
              placeholder="Horário desejado (opcional, ex: 14:00)"
              value={horarioDesejado}
              onChangeText={setHorarioDesejado}
            />
            <TextInput
              style={styles.input}
              placeholder="Observações (opcional)"
              value={observacoesFila}
              onChangeText={setObservacoesFila}
              multiline
            />
          </View>
        )}

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Dados do cliente</Text>
          <Text style={styles.sectionDesc}>
            Campos com * são obrigatórios para reserva e fila de espera.
          </Text>
          <TextInput
            style={styles.input}
            placeholder="Nome completo *"
            value={nome}
            onChangeText={setNome}
            autoCapitalize="words"
          />
          {telefoneCadastrado ? (
            <>
              <View style={styles.telefoneCadastradoBox}>
                <Text style={styles.telefoneCadastradoLabel}>Telefone cadastrado</Text>
                <Text style={styles.telefoneCadastradoValor}>{telefoneCadastrado}</Text>
              </View>
              <TextInput
                style={styles.input}
                placeholder="Confirmar telefone *"
                value={confirmarTelefone}
                onChangeText={setConfirmarTelefone}
                keyboardType="phone-pad"
              />
            </>
          ) : (
            <TextInput
              style={styles.input}
              placeholder="Telefone *"
              value={telefone}
              onChangeText={setTelefone}
              keyboardType="phone-pad"
            />
          )}
          <TextInput
            style={styles.input}
            placeholder="E-mail"
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
          />
        </View>

        <View style={styles.resumo}>
          <Text style={styles.resumoTitle}>Resumo</Text>
          <View style={styles.resumoItem}>
            <Text style={styles.resumoLabel}>Trança:</Text>
            <Text style={styles.resumoValue}>{tranca.nome}</Text>
          </View>
          {fotoSelecionada && (
            <View style={styles.resumoItem}>
              <Text style={styles.resumoLabel}>Modelo:</Text>
              <Text style={styles.resumoValue}>{fotoSelecionada.nome}</Text>
            </View>
          )}
          <View style={styles.resumoItem}>
            <Text style={styles.resumoLabel}>Valor total:</Text>
            <Text style={styles.resumoValue}>
              {formatarMoeda(valorTotal)}
            </Text>
          </View>
          <View style={styles.resumoItem}>
            <Text style={styles.resumoLabel}>Sinal ({labelPercentualSinal()}):</Text>
            <Text style={[styles.resumoValue, styles.sinal]}>
              {formatarMoeda(valorSinal)}
            </Text>
          </View>
          <View style={styles.resumoItem}>
            <Text style={styles.resumoLabel}>Restante (no atendimento):</Text>
            <Text style={styles.resumoValue}>
              {formatarMoeda(valorRestante)}
            </Text>
          </View>
        </View>

        {!modoFila && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Comprovante de depósito</Text>
          <Text style={styles.sectionDesc}>
            Faça o depósito do sinal ({formatarMoeda(valorSinal)}) e anexe o comprovante
            para agilizar a confirmação da reserva.
          </Text>
          <ComprovantePicker value={comprovante} onChange={setComprovante} />
        </View>
        )}

        <ButtonPrimary
          title={modoFila ? 'Entrar na Fila de Espera' : 'Confirmar Agendamento'}
          onPress={handleAgendar}
          loading={submitting}
        />
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  content: {
    padding: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#333',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 15,
    color: '#666',
    marginBottom: 24,
  },
  erroModelo: {
    fontSize: 16,
    color: '#DC3545',
    textAlign: 'center',
    marginTop: 40,
    padding: 20,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 12,
  },
  sectionDesc: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
    marginBottom: 12,
  },
  horarios: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  input: {
    borderWidth: 1,
    borderColor: '#DDD',
    borderRadius: 8,
    padding: 16,
    fontSize: 16,
    marginBottom: 12,
    backgroundColor: '#FFF',
  },
  resumo: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 24,
  },
  resumoTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#333',
    marginBottom: 12,
  },
  resumoItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  resumoLabel: {
    fontSize: 14,
    color: '#666',
  },
  resumoValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  sinal: {
    color: '#7B2CBF',
    fontSize: 18,
  },
  hojeBtn: {
    marginTop: 12,
    padding: 14,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#E67E22',
    alignItems: 'center',
  },
  hojeBtnText: {
    color: '#E67E22',
    fontWeight: '700',
    fontSize: 15,
  },
  filaBox: {
    backgroundColor: '#FFF8E7',
    borderRadius: 12,
    padding: 16,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: '#F0D78C',
  },
  filaTitulo: {
    fontSize: 16,
    fontWeight: '700',
    color: '#333',
    marginBottom: 8,
  },
  filaDesc: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
    marginBottom: 12,
  },
  telefoneCadastradoBox: {
    backgroundColor: '#F3E8FF',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#D4BBF0',
  },
  telefoneCadastradoLabel: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  telefoneCadastradoValor: {
    fontSize: 16,
    fontWeight: '700',
    color: '#7B2CBF',
  },
});
