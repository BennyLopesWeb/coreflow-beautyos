"""
Service de Financeiro
Lógica de negócio para gerenciamento financeiro
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from app.models.financeiro import Financeiro, TipoMovimento
from app.schemas.financeiro import SaidaCreate, ResumoFinanceiroResponse
from app.core.exceptions import ValidationError


class FinanceiroService:
    """
    Service para gerenciamento financeiro
    Centraliza lógica de entradas e saídas
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def registrar_entrada_automatica(
        self,
        descricao: str,
        valor: Decimal,
        agendamento_id: Optional[int] = None
    ) -> Financeiro:
        """
        Registra entrada financeira automática (ex.: pagamento de sinal/final).

        Chamado automaticamente pelo sistema ao confirmar pagamentos.

        .. deprecated:: 2.11.0-r4-f8
            ``agendamento_id`` passou a ser opcional — a tabela
            ``agendamentos`` foi removida (DROP físico — ADR-024 sunset /
            RFC-003 M11+). Para bookings core-only, chame com
            ``agendamento_id=None`` (coluna histórica, sem FK física desde
            R4-F7).

        Args:
            descricao: Texto descritivo do movimento (ex.: "Sinal - Booking #12").
            valor: Valor monetário da entrada.
            agendamento_id: ID legado opcional, mantido apenas para
                rastreabilidade histórica (sem FK física).

        Returns:
            Registro ``Financeiro`` persistido.
        """
        movimento = Financeiro(
            tipo=TipoMovimento.ENTRADA,
            descricao=descricao,
            valor=valor,
            agendamento_id=agendamento_id,
            data=datetime.now()
        )
        
        self.db.add(movimento)
        self.db.commit()
        self.db.refresh(movimento)
        
        return movimento
    
    def registrar_saida(self, saida_data: SaidaCreate) -> Financeiro:
        """
        Registra saída manual
        Valida valor antes de registrar
        """
        if saida_data.valor <= 0:
            raise ValidationError("Valor da saída deve ser maior que zero")
        
        movimento = Financeiro(
            tipo=TipoMovimento.SAIDA,
            descricao=saida_data.descricao,
            valor=saida_data.valor,
            agendamento_id=None,
            data=saida_data.data or datetime.now()
        )
        
        self.db.add(movimento)
        self.db.commit()
        self.db.refresh(movimento)
        
        return movimento
    
    def obter_resumo(
        self,
        inicio: datetime,
        fim: datetime
    ) -> ResumoFinanceiroResponse:
        """
        Obtém resumo financeiro do período
        Calcula totais de entradas, saídas e saldo
        """
        # Busca movimentos do período
        movimentos = self.db.query(Financeiro).filter(
            Financeiro.data >= inicio,
            Financeiro.data <= fim
        ).order_by(Financeiro.data).all()
        
        # Calcula totais
        total_entradas = self.db.query(func.sum(Financeiro.valor)).filter(
            Financeiro.tipo == TipoMovimento.ENTRADA,
            Financeiro.data >= inicio,
            Financeiro.data <= fim
        ).scalar() or Decimal("0.00")
        
        total_saidas = self.db.query(func.sum(Financeiro.valor)).filter(
            Financeiro.tipo == TipoMovimento.SAIDA,
            Financeiro.data >= inicio,
            Financeiro.data <= fim
        ).scalar() or Decimal("0.00")
        
        saldo = total_entradas - total_saidas
        
        return ResumoFinanceiroResponse(
            inicio=inicio,
            fim=fim,
            total_entradas=total_entradas,
            total_saidas=total_saidas,
            saldo=saldo,
            movimentos=movimentos
        )

