"""
Configuração de logging estruturado
"""
import logging
import sys
from app.core.config import settings

# Configura logging básico
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Logger principal
logger = logging.getLogger("trancapro")

def get_logger(name: str = None):
    """
    Obtém logger configurado
    """
    if name:
        return logging.getLogger(f"trancapro.{name}")
    return logger

