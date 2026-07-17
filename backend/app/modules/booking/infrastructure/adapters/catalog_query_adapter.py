"""
Re-export — adapter canônico vive em ``modules/catalog`` (R2-F3b).
"""
from app.modules.catalog.infrastructure.adapters.catalog_query_adapter import (
    SqlAlchemyCatalogQueryAdapter,
)

__all__ = ["SqlAlchemyCatalogQueryAdapter"]
