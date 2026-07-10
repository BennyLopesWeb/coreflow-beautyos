"""
Router de Pagamentos
Endpoints para pagamento de sinal via Pix e comprovante de depósito
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.pagamento import (
    PagamentoSinalRequest,
    PagamentoSinalResponse,
    ComprovanteUploadResponse,
)
from app.services.agendamento_service import AgendamentoService
from app.services.comprovante_service import ComprovanteService
from app.integrations.pix import PixService
from app.core.config import settings
from app.core.exceptions import ValidationError

router = APIRouter(prefix="/pagamentos", tags=["Pagamentos"])


@router.post("/sinal", response_model=PagamentoSinalResponse)
def confirmar_pagamento_sinal(
    pagamento_data: PagamentoSinalRequest,
    db: Session = Depends(get_db)
):
    """
    Confirma pagamento do sinal
    Em produção, validar com gateway Pix real via webhook
    """
    if not settings.PIX_MOCK_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Pagamento Pix não está habilitado"
        )
    
    service = AgendamentoService(db)
    pix_service = PixService()
    
    try:
        agendamento = service.obter_agendamento(pagamento_data.agendamento_id)
        
        if pagamento_data.transaction_id:
            pagamento_info = pix_service.verificar_pagamento(pagamento_data.transaction_id)
            if pagamento_info["status"] != "pago":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Pagamento não confirmado no gateway"
                )
        
        agendamento_atualizado = service.confirmar_sinal(pagamento_data.agendamento_id)
        
        return PagamentoSinalResponse(
            agendamento_id=agendamento_atualizado.id,
            sinal_pago=agendamento_atualizado.sinal_pago,
            mensagem="Pagamento do sinal confirmado com sucesso"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/sinal/gerar", response_model=dict)
def gerar_cobranca_pix(
    agendamento_id: int,
    db: Session = Depends(get_db)
):
    """
    Gera cobrança Pix para o sinal
    Retorna QR Code e código Pix
    """
    if not settings.PIX_MOCK_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Pagamento Pix não está habilitado"
        )
    
    service = AgendamentoService(db)
    pix_service = PixService()
    
    try:
        agendamento = service.obter_agendamento(agendamento_id)
        
        if agendamento.sinal_pago:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sinal já foi pago"
            )
        
        from app.models.tranca import Tranca
        from app.utils.service_image_precos import resolver_precos_imagem

        tranca = db.query(Tranca).filter(Tranca.id == agendamento.tranca_id).first()
        
        if not tranca:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trança não encontrada"
            )

        if not agendamento.service_image:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agendamento sem foto/modelo selecionado"
            )

        valor_sinal = agendamento.valor_sinal
        if valor_sinal is None:
            precos = resolver_precos_imagem(agendamento.service_image)
            valor_sinal = precos["valor_sinal"]

        from app.schemas.service_image import _label_modelo
        descricao = (
            f"Sinal - Agendamento #{agendamento.id} - "
            f"{tranca.nome} — {_label_modelo(agendamento.service_image)}"
        )
        
        cobranca = pix_service.criar_cobranca(
            valor=valor_sinal,
            descricao=descricao,
            expiracao_minutos=30
        )
        
        return {
            "agendamento_id": agendamento_id,
            "valor": str(valor_sinal),
            "qr_code": cobranca["qr_code"],
            "pix_code": cobranca["pix_code"],
            "transaction_id": cobranca["transaction_id"],
            "expires_at": cobranca["expires_at"].isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/comprovante/{agendamento_id}",
    response_model=ComprovanteUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def enviar_comprovante_deposito(
    agendamento_id: int,
    request: Request,
    arquivo: UploadFile = File(..., description="Comprovante de depósito (JPG, PNG, WEBP ou PDF)"),
    db: Session = Depends(get_db),
):
    """
    Envia comprovante de depósito do sinal vinculado ao agendamento.
    O pagamento será analisado pelo administrador antes da confirmação.
    """
    service = ComprovanteService(db)
    base_url = str(request.base_url).rstrip("/")
    try:
        agendamento = await service.salvar_comprovante(
            agendamento_id,
            arquivo,
            base_url=base_url,
        )
        return ComprovanteUploadResponse(
            agendamento_id=agendamento.id,
            comprovante_url=agendamento.comprovante_url,
            mensagem=(
                "Comprovante recebido com sucesso. "
                "Aguarde a confirmação do pagamento pelo salão."
            ),
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
