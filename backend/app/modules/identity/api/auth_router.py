"""
Router de autenticação — módulo Identity (API adapter).
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.auth import (
    UserCreate,
    UserResponse,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
)
from app.schemas.company import UserMeResponse
from app.models.user import User
from app.modules.identity.api.deps import (
    get_identity_service,
    get_current_active_user,
)
from app.modules.identity.application.identity_service import IdentityApplicationService

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate,
    identity: IdentityApplicationService = Depends(get_identity_service),
):
    """
    Registra novo usuário (cliente) e associa ao tenant demo.

    Returns:
        UserResponse do usuário criado.
    """
    try:
        return identity.register_user(user_data)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/login", response_model=TokenResponse)
def login(
    login_data: LoginRequest,
    identity: IdentityApplicationService = Depends(get_identity_service),
):
    """
    Login com JWT incluindo company_id e role.

    Returns:
        Tokens access + refresh.
    """
    try:
        return identity.login(login_data)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    refresh_data: RefreshTokenRequest,
    identity: IdentityApplicationService = Depends(get_identity_service),
):
    """
    Renova access token via refresh token.

    Returns:
        Novo access token.
    """
    try:
        return identity.refresh_access_token(refresh_data.refresh_token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


@router.get("/me", response_model=UserMeResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
    identity: IdentityApplicationService = Depends(get_identity_service),
):
    """
    Perfil do usuário autenticado com contexto de tenant BeautyOS.

    Returns:
        UserMeResponse.
    """
    return identity.get_user_profile(current_user)
