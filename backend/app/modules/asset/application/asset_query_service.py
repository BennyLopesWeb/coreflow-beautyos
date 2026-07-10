"""
Consultas read-only de Asset genérico CoreFlow.
"""
from typing import List

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.asset.domain.models import CoreAsset


class AssetQueryService:
    """
    Serviço de leitura para core_assets.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def list_assets(self, company_id: int) -> List[CoreAsset]:
        """
        Lista ativos do tenant.

        Args:
            company_id: Tenant.

        Returns:
            Lista de CoreAsset ativos.
        """
        return (
            self.db.query(CoreAsset)
            .filter(
                CoreAsset.company_id == company_id,
                CoreAsset.deleted_at.is_(None),
                CoreAsset.active.is_(True),
            )
            .order_by(CoreAsset.name.asc())
            .all()
        )

    def get_asset(self, asset_id: int, company_id: int) -> CoreAsset:
        """
        Obtém ativo por ID com escopo de tenant.

        Args:
            asset_id: ID core_assets.
            company_id: Tenant.

        Returns:
            CoreAsset.

        Raises:
            NotFoundError: Se não encontrado.
        """
        row = (
            self.db.query(CoreAsset)
            .filter(
                CoreAsset.id == asset_id,
                CoreAsset.company_id == company_id,
                CoreAsset.deleted_at.is_(None),
            )
            .first()
        )
        if not row:
            raise NotFoundError("Asset", str(asset_id))
        return row
