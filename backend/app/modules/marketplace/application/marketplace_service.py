"""
Marketplace Service — catálogo cloud proto + instalação de plugins por tenant.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.core.plugin.registry import plugin_registry
from app.models.company import Company

logger = get_logger("marketplace")

CATALOG_PATH = Path(__file__).resolve().parents[3] / "marketplace" / "catalog.yaml"


class MarketplaceService:
    """
    Serviço do marketplace CoreFlow (proto CF-10).

    Mescla catálogo cloud (YAML) com plugins locais instalados e permite
    ativar plugin em um tenant via ``company.plugin_id``.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def list_listings(self, company_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Lista plugins do marketplace com flag ``installed`` por tenant.

        Args:
            company_id: Tenant para marcar plugin ativo (opcional).

        Returns:
            Lista de listings serializáveis.
        """
        installed_plugin_id = None
        if company_id:
            company = self.db.query(Company).filter(Company.id == company_id).first()
            if company:
                installed_plugin_id = company.plugin_id

        local_ids = {p.plugin_id for p in plugin_registry.list_all()}
        listings: List[Dict[str, Any]] = []

        for entry in self._load_catalog():
            plugin_id = entry["plugin_id"]
            local = plugin_registry.get(plugin_id)
            listings.append(
                {
                    **entry,
                    "installed": plugin_id == installed_plugin_id,
                    "available_locally": plugin_id in local_ids,
                    "local_version": local.version if local else None,
                }
            )

        for manifest in plugin_registry.list_all():
            if any(l["plugin_id"] == manifest.plugin_id for l in listings):
                continue
            listings.append(
                {
                    "plugin_id": manifest.plugin_id,
                    "name": manifest.name,
                    "version": manifest.version,
                    "description": manifest.description,
                    "product_name": manifest.product_name,
                    "source": "local",
                    "installable": True,
                    "pricing": "free",
                    "min_platform_version": manifest.sdk.get(
                        "min_platform_version", "0.1.0"
                    ),
                    "installed": manifest.plugin_id == installed_plugin_id,
                    "available_locally": True,
                    "local_version": manifest.version,
                }
            )

        return sorted(listings, key=lambda x: x["plugin_id"])

    def install_plugin(self, company_id: int, plugin_id: str) -> Company:
        """
        Instala/ativa plugin no tenant (altera ``company.plugin_id``).

        Args:
            company_id: ID da empresa.
            plugin_id: ID do plugin a instalar.

        Returns:
            Company atualizada.

        Raises:
            ValueError: Se plugin não instalável ou não encontrado.
        """
        listing = next(
            (l for l in self.list_listings(company_id) if l["plugin_id"] == plugin_id),
            None,
        )
        if not listing:
            raise ValueError(f"Plugin '{plugin_id}' não encontrado no marketplace")
        if not listing.get("installable"):
            raise ValueError(
                f"Plugin '{plugin_id}' ainda não está disponível para instalação"
            )
        if not listing.get("available_locally"):
            raise ValueError(
                f"Plugin '{plugin_id}' não está instalado localmente no servidor"
            )

        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError(f"Empresa {company_id} não encontrada")

        company.plugin_id = plugin_id
        self.db.commit()
        self.db.refresh(company)
        logger.info(f"Plugin {plugin_id} instalado em company={company_id}")
        return company

    def _load_catalog(self) -> List[Dict[str, Any]]:
        """
        Carrega catálogo cloud de YAML.

        Returns:
            Lista de entradas do catálogo.
        """
        if not CATALOG_PATH.is_file():
            logger.warning(f"Catálogo marketplace não encontrado: {CATALOG_PATH}")
            return []
        with open(CATALOG_PATH, encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
        if isinstance(data, list):
            return data
        return [data] if data else []
