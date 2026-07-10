"""
Schemas do painel administrativo.
"""
from pydantic import BaseModel
from datetime import datetime, date
from typing import List, Optional
from decimal import Decimal
from app.models.agendamento import StatusAgendamento


class AdminDashboardResponse(BaseModel):
    """Resumo geral para o dashboard admin."""
    total_clientes: int
    total_agendamentos: int
    agendamentos_pendentes: int
    aguardando_aprovacao: int = 0
    agendamentos_confirmados: int
    agendamentos_hoje: int
    fila_hoje: int
    pagamentos_pendentes: int
    pagamentos_confirmados: int
    receita_mes: Decimal
    saldo_mes: Decimal


class PagamentoAdminItem(BaseModel):
    """Item de pagamento para listagem admin."""
    agendamento_id: int
    cliente_nome: str
    tranca_nome: str
    valor_sinal: Decimal
    sinal_pago: bool
    comprovante_url: Optional[str] = None
    status_agendamento: StatusAgendamento
    data_hora: datetime


class AgendamentoAdminItem(BaseModel):
    """Agendamento com dados relacionados para gestão admin."""
    id: int
    cliente_id: int
    cliente_nome: str
    cliente_telefone: str
    tranca_id: int
    tranca_nome: str
    data_hora: datetime
    status: StatusAgendamento
    sinal_pago: bool
    na_fila: bool
    posicao_fila: Optional[int] = None
    service_image_id: Optional[int] = None
    imagem_url: Optional[str] = None
    imagem_label: Optional[str] = None


class ClienteCrmItem(BaseModel):
    """Cliente com métricas de CRM."""
    id: int
    nome: str
    telefone: str
    email: Optional[str] = None
    total_agendamentos: int
    agendamentos_confirmados: int
    total_gasto: Decimal
    ultima_visita: Optional[datetime] = None
    status_crm: str


class AtualizarStatusAgendamentoRequest(BaseModel):
    """Request para atualizar status de agendamento."""
    status: StatusAgendamento
