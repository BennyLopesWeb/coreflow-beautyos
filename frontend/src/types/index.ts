/**
 * Tipos TypeScript
 * Definições de tipos para o app
 */

// User
export interface User {
  id: number;
  email: string;
  nome: string;
  telefone?: string;
  ativo: boolean;
  is_superuser?: boolean;
  created_at: string;
}

// Auth
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  nome: string;
  password: string;
  telefone: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// Tranca
export interface TrancaImagem {
  id: number;
  url: string;
  ordem: number;
  is_principal: boolean;
  nome: string;
  descricao?: string;
  nivel_complexidade?: string;
  quantidade_trancas?: number;
  quantidade_cabelo?: string;
  ativo?: boolean;
  label: string;
  valor_total: string;
  valor_sinal: string;
  valor_restante?: string;
  duracao_minutos: number;
  percentual_sinal?: string;
}

export interface TrancaImagemUpdate {
  nome?: string;
  descricao?: string;
  nivel_complexidade?: string;
  quantidade_trancas?: number;
  quantidade_cabelo?: string;
  valor_total?: string;
  duracao_minutos?: number;
  percentual_sinal?: string;
  ativo?: boolean;
}

export interface Tranca {
  id: number;
  nome: string;
  descricao?: string;
  imagens: string[];
  ativo: boolean;
}

export interface TrancaCreate {
  nome: string;
  descricao?: string;
  imagens?: string[];
  ativo?: boolean;
}

export interface TrancaUpdate {
  nome?: string;
  descricao?: string;
  imagens?: string[];
  ativo?: boolean;
}

// Cliente
export interface Cliente {
  id: number;
  nome: string;
  telefone: string;
  email?: string;
}

// Agendamento
export type StatusAgendamento =
  | 'pending_payment'
  | 'pending_approval'
  | 'waiting_time_confirmation'
  | 'approved'
  | 'rejected'
  | 'in_queue'
  | 'checked_in'
  | 'in_service'
  | 'completed'
  | 'paid'
  | 'cancelled'
  // Legado
  | 'pendente'
  | 'confirmado'
  | 'cancelado'
  | 'concluido'
  | 'no_show';

export type ReservationStatus = StatusAgendamento;

export type StatusFila =
  | 'waiting'
  | 'contacted'
  | 'approved'
  | 'rejected'
  | 'cancelled';

export type StatusPagamento =
  | 'pending_payment'
  | 'partially_paid'
  | 'confirmed'
  | 'cancelled';

export interface Agendamento {
  id: number;
  cliente_id: number;
  tranca_id: number;
  data_hora: string;
  sinal_pago: boolean;
  comprovante_url?: string;
  service_image_id?: number;
  modelo_nome?: string;
  imagem_url?: string;
  imagem_label?: string;
  valor_total_reserva?: string;
  valor_sinal_reserva?: string;
  valor_restante_reserva?: string;
  duracao_reserva_minutos?: number;
  status_pagamento?: StatusPagamento;
  status: StatusAgendamento;
  observacoes?: string;
  cliente?: Cliente;
  tranca?: Tranca;
}

export interface AgendamentoCreate {
  cliente_id: number;
  tranca_id: number;
  service_image_id: number;
  data_hora: string;
  observacoes?: string;
}

// Disponibilidade
export interface HorarioDisponivel {
  horario: string;
  disponivel: boolean;
}

export interface DisponibilidadeResponse {
  data: string;
  tranca_id: number;
  horarios: HorarioDisponivel[];
}

// CoreFlow v1
export interface CatalogV1 {
  id: number;
  company_id: number;
  name: string;
  slug: string;
  legacy_tranca_id?: number | null;
  active: boolean;
}

export interface OfferingV1 {
  id: number;
  catalog_id: number;
  name?: string | null;
  legacy_service_image_id?: number | null;
  duration_minutes?: number | null;
  active: boolean;
}

export interface AvailabilitySlot {
  starts_at: string;
  available: boolean;
  duration_minutes?: number | null;
  catalog_id: number;
  offering_id: number;
  resource_id?: number | null;
  worker_id?: number | null;
}

export interface BookingV1 {
  id: number;
  legacy_agendamento_id?: number | null;
  customer_id: number;
  catalog_id: number;
  offering_id: number;
  scheduled_at: string;
  status: string;
  payment_status: string;
  price_total: string;
  deposit_amount: string;
  deposit_paid: boolean;
  remaining_amount?: string;
  notes?: string | null;
}

// Pagamento
export interface PixCobranca {
  agendamento_id: number;
  valor: string;
  qr_code: string;
  pix_code: string;
  transaction_id: string;
  expires_at: string;
}

export interface ComprovanteUploadResponse {
  agendamento_id: number;
  comprovante_url: string;
  mensagem: string;
}

// Financeiro
export interface ResumoFinanceiro {
  inicio: string;
  fim: string;
  total_entradas: string;
  total_saidas: string;
  saldo: string;
  movimentos: MovimentoFinanceiro[];
}

export interface MovimentoFinanceiro {
  id: number;
  tipo: 'entrada' | 'saida';
  descricao: string;
  valor: string;
  data: string;
}

// Fila de espera
export interface FilaEsperaCreate {
  cliente_id: number;
  tranca_id: number;
  service_image_id: number;
  data_desejada: string;
  horario_desejado?: string;
  observacoes?: string;
  mesmo_dia?: boolean;
}

export interface FilaItem {
  id: number;
  posicao: number;
  cliente_id: number;
  cliente_nome: string;
  cliente_telefone: string;
  tranca_id: number;
  tranca_nome: string;
  service_image_id: number;
  modelo_nome: string;
  data: string;
  horario_desejado?: string;
  observacoes?: string;
  mesmo_dia: boolean;
  status: StatusFila;
  agendamento_id?: number;
  created_at: string;
}

export interface FilaResumo {
  data: string;
  total_pessoas: number;
  posicoes: FilaItem[];
}

// Admin
export interface AdminDashboard {
  total_clientes: number;
  total_agendamentos: number;
  agendamentos_pendentes: number;
  aguardando_aprovacao?: number;
  agendamentos_confirmados: number;
  agendamentos_hoje: number;
  fila_hoje: number;
  pagamentos_pendentes: number;
  pagamentos_confirmados: number;
  receita_mes: string;
  saldo_mes: string;
}

export interface PagamentoAdmin {
  agendamento_id: number;
  cliente_nome: string;
  tranca_nome: string;
  valor_sinal: string;
  sinal_pago: boolean;
  comprovante_url?: string;
  status_agendamento: StatusAgendamento;
  data_hora: string;
}

export interface AgendamentoAdmin {
  id: number;
  cliente_id: number;
  cliente_nome: string;
  cliente_telefone: string;
  tranca_id: number;
  tranca_nome: string;
  data_hora: string;
  status: StatusAgendamento;
  sinal_pago: boolean;
  na_fila: boolean;
  posicao_fila?: number;
  service_image_id?: number;
  imagem_url?: string;
  imagem_label?: string;
}

export interface ClienteCrm {
  id: number;
  nome: string;
  telefone: string;
  email?: string;
  total_agendamentos: number;
  agendamentos_confirmados: number;
  total_gasto: string;
  ultima_visita?: string;
  status_crm: 'novo' | 'ativo' | 'inativo' | 'pendente_pagamento';
}

export type AgentTaskType =
  | 'lembrete_pagamento'
  | 'reativar_cliente'
  | 'notificar_fila'
  | 'confirmar_agendamento'
  | 'follow_up';

export type AgentTaskStatus = 'pendente' | 'executada' | 'cancelada';

export interface AgentTask {
  id: number;
  tipo: AgentTaskType;
  titulo: string;
  descricao: string;
  status: AgentTaskStatus;
  referencia_id?: number;
  resultado?: string;
  created_at: string;
  executed_at?: string;
}

export interface AgenteExecutarResponse {
  tarefas_criadas: number;
  tarefas_executadas: number;
  mensagem: string;
  tarefas: AgentTask[];
}

