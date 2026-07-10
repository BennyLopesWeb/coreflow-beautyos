"""
Router de Tranças
Endpoints para gerenciamento de tranças
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request, Query
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.core.dependencies import (
    get_current_active_user,
    get_current_admin,
    get_current_admin_user,
    get_tenant_context,
)
from app.core.tenant import TenantContext
from app.models.user import User
from app.schemas.tranca import TrancaCreate, TrancaUpdate, TrancaResponse, TrancaImagensUpdate
from app.schemas.service_image import TrancaImagemResponse, TrancaImagemUpdate
from app.services.tranca_service import TrancaService
from app.services.service_image_service import ServiceImageService
from app.core.exceptions import ValidationError

router = APIRouter(prefix="/trancas", tags=["Tranças"])


@router.get("", response_model=List[TrancaResponse])
def listar_trancas(
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    Lista tranças ativas do tenant (catálogo público).
    """
    service = TrancaService(db)
    return service.listar_trancas_ativas(company_id=tenant.company_id)


@router.post("", response_model=TrancaResponse, status_code=status.HTTP_201_CREATED)
def criar_tranca(
    tranca_data: TrancaCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_admin),
):
    """
    Cria nova trança. Apenas administradores.
    """
    service = TrancaService(db)
    try:
        return service.criar_tranca(tranca_data, company_id=tenant.company_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{tranca_id}", response_model=TrancaResponse)
def obter_tranca(
    tranca_id: int,
    db: Session = Depends(get_db)
):
    """Obtém detalhes de uma trança"""
    service = TrancaService(db)
    try:
        return service.obter_tranca(tranca_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.put("/{tranca_id}", response_model=TrancaResponse)
def atualizar_tranca(
    tranca_id: int,
    tranca_data: TrancaUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """Atualiza trança existente. Apenas administradores."""
    service = TrancaService(db)
    try:
        return service.atualizar_tranca(tranca_id, tranca_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{tranca_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_tranca(
    tranca_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """Deleta trança (soft delete). Apenas administradores."""
    service = TrancaService(db)
    try:
        service.deletar_tranca(tranca_id)
        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{tranca_id}/imagens", response_model=TrancaResponse)
def definir_imagens_tranca(
    tranca_id: int,
    body: TrancaImagensUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Define a galeria completa de fotos (Foto 1, Foto 2, ... Foto N).
    Apenas administradores.
    """
    service = TrancaService(db)
    try:
        return service.definir_imagens(tranca_id, body.imagens)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{tranca_id}/imagens", response_model=TrancaResponse)
async def adicionar_imagem_tranca(
    tranca_id: int,
    request: Request,
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Adiciona uma foto à galeria da trança (append). Apenas administradores.
    """
    service = TrancaService(db)
    base_url = str(request.base_url).rstrip("/")
    try:
        return await service.adicionar_imagem(tranca_id, arquivo, base_url=base_url)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{tranca_id}/imagens/sincronizar", response_model=TrancaResponse)
def sincronizar_imagens_tranca(
    tranca_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Sincroniza foto principal do disco ({slug}.png). Apenas administradores.
    """
    service = TrancaService(db)
    base_url = str(request.base_url).rstrip("/")
    try:
        return service.sincronizar_imagens_do_disco(tranca_id, base_url=base_url)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{tranca_id}/imagens", response_model=List[TrancaImagemResponse])
def listar_imagens_tranca(
    tranca_id: int,
    db: Session = Depends(get_db),
):
    """
    Lista modelos da categoria (preços vêm do modelo, não da categoria).
    """
    image_service = ServiceImageService(db)
    tranca_service = TrancaService(db)
    tranca_service.obter_tranca(tranca_id)
    imagens = image_service.listar_por_tranca(tranca_id)
    return [
        TrancaImagemResponse.from_model(img, exigir_precos=False)
        for img in imagens
    ]


@router.patch("/{tranca_id}/imagens/{imagem_id}", response_model=TrancaImagemResponse)
def atualizar_imagem_tranca(
    tranca_id: int,
    imagem_id: int,
    body: TrancaImagemUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Atualiza preços e duração de uma foto/modelo específico. Apenas administradores.
    """
    image_service = ServiceImageService(db)
    tranca_service = TrancaService(db)
    try:
        data = body.model_dump(exclude_unset=True)
        img = image_service.atualizar_imagem(tranca_id, imagem_id, **data)
        tranca = tranca_service.obter_tranca(tranca_id)
        return TrancaImagemResponse.from_model(img, tranca)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{tranca_id}/imagens/{imagem_id}",
    response_model=List[TrancaImagemResponse],
)
def remover_imagem_tranca(
    tranca_id: int,
    imagem_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Remove uma foto do álbum da trança (admin).
    """
    tranca_service = TrancaService(db)
    image_service = ServiceImageService(db)
    try:
        tranca_service.remover_imagem(tranca_id, imagem_id)
        tranca = tranca_service.obter_tranca(tranca_id)
        imagens = image_service.listar_por_tranca(tranca_id)
        return [TrancaImagemResponse.from_model(img, tranca) for img in imagens]
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
