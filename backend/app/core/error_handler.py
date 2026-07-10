"""
Handler global de exceções
Tratamento centralizado de erros
"""
from fastapi import Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.logging_config import get_logger
from app.core.config import settings

logger = get_logger("error_handler")


async def trancapro_exception_handler(request: Request, exc: HTTPException):
    """
    Handler para exceções customizadas da aplicação
    """
    logger.error(
        f"Erro na requisição {request.method} {request.url.path}",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "path": request.url.path
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handler para erros de validação do Pydantic
    """
    errors = exc.errors()
    logger.warning(
        f"Erro de validação em {request.method} {request.url.path}",
        extra={"errors": errors}
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "message": "Erro de validação",
            "errors": errors,
            "path": request.url.path
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """
    Handler genérico para exceções não tratadas
    """
    logger.exception(
        f"Erro não tratado em {request.method} {request.url.path}",
        exc_info=exc
    )
    
    response_content = {
        "error": True,
        "message": "Erro interno do servidor",
        "path": request.url.path
    }
    
    # Em modo debug, inclui detalhes do erro
    if settings.DEBUG:
        response_content["detail"] = str(exc)
        response_content["type"] = type(exc).__name__
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response_content
    )

