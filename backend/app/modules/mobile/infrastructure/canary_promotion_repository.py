"""
CanaryPromotionRepository — persistência de promoções canary (CF-25).
"""
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.mobile.domain.models import CoreCanaryPromotion


class CanaryPromotionRepository:
    """
    CRUD para ``core_canary_promotions`` com fallback in-memory opcional.

    Quando ``MOBILE_EAS_UPDATE_CANARY_PERSIST_DB=true``, usa SQLAlchemy
    (sessão injetada ou ``SessionLocal`` automático).
    """

    _MEMORY_STORE: Dict[str, Dict[str, Any]] = {}

    def __init__(self, db: Optional[Session] = None):
        """
        Args:
            db: Sessão SQLAlchemy opcional.
        """
        self.db = db

    @staticmethod
    def state_key(plugin_id: str, segment: str) -> str:
        """
        Chave única plugin + segmento.

        Args:
            plugin_id: ID do plugin.
            segment: Segmento canary.

        Returns:
            String ``plugin_id:segment``.
        """
        return f"{plugin_id}:{segment}"

    def _use_db(self) -> bool:
        """
        Indica se persistência DB está ativa.

        Returns:
            True se setting de persistência habilitado.
        """
        return settings.MOBILE_EAS_UPDATE_CANARY_PERSIST_DB

    @contextmanager
    def _db_session(self) -> Iterator[Optional[Session]]:
        """
        Fornece sessão DB injetada ou abre ``SessionLocal`` temporário.

        Yields:
            Sessão SQLAlchemy quando persistência DB ativa; None caso contrário.
        """
        if not self._use_db():
            yield None
            return

        if self.db is not None:
            yield self.db
            return

        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def save_promotion(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Grava ou atualiza promoção canary ativa.

        Args:
            state: Dict plugin_id, segment, branches, production_channel.

        Returns:
            Estado persistido com id quando DB.
        """
        key = self.state_key(state["plugin_id"], state["segment"])

        with self._db_session() as db:
            if db is not None:
                row = (
                    db.query(CoreCanaryPromotion)
                    .filter(
                        CoreCanaryPromotion.plugin_id == state["plugin_id"],
                        CoreCanaryPromotion.segment == state["segment"],
                    )
                    .first()
                )
                if row is None:
                    row = CoreCanaryPromotion(
                        plugin_id=state["plugin_id"],
                        segment=state["segment"],
                        previous_branch=state["previous_branch"],
                        promoted_branch=state["promoted_branch"],
                        production_channel=state["production_channel"],
                        active=True,
                    )
                    db.add(row)
                else:
                    row.previous_branch = state["previous_branch"]
                    row.promoted_branch = state["promoted_branch"]
                    row.production_channel = state["production_channel"]
                    row.active = True
                    row.rolled_back_at = None
                db.commit()
                db.refresh(row)
                return self._row_to_dict(row)

        state = {**state, "promoted": True}
        self._MEMORY_STORE[key] = state
        return state

    def get_active(self, plugin_id: str, segment: str) -> Optional[Dict[str, Any]]:
        """
        Busca promoção ativa por plugin + segmento.

        Args:
            plugin_id: ID do plugin.
            segment: Segmento canary.

        Returns:
            Dict estado ou None.
        """
        with self._db_session() as db:
            if db is not None:
                row = (
                    db.query(CoreCanaryPromotion)
                    .filter(
                        CoreCanaryPromotion.plugin_id == plugin_id,
                        CoreCanaryPromotion.segment == segment,
                        CoreCanaryPromotion.active.is_(True),
                    )
                    .first()
                )
                return self._row_to_dict(row) if row else None

        return self._MEMORY_STORE.get(self.state_key(plugin_id, segment))

    def list_active(self) -> List[Dict[str, Any]]:
        """
        Lista todas promoções canary ativas.

        Returns:
            Lista de dicts de promoção.
        """
        with self._db_session() as db:
            if db is not None:
                rows = (
                    db.query(CoreCanaryPromotion)
                    .filter(CoreCanaryPromotion.active.is_(True))
                    .all()
                )
                return [self._row_to_dict(r) for r in rows]

        return list(self._MEMORY_STORE.values())

    def mark_rolled_back(self, plugin_id: str, segment: str) -> None:
        """
        Marca promoção como revertida (inativa).

        Args:
            plugin_id: ID do plugin.
            segment: Segmento canary.

        Returns:
            None
        """
        with self._db_session() as db:
            if db is not None:
                row = (
                    db.query(CoreCanaryPromotion)
                    .filter(
                        CoreCanaryPromotion.plugin_id == plugin_id,
                        CoreCanaryPromotion.segment == segment,
                        CoreCanaryPromotion.active.is_(True),
                    )
                    .first()
                )
                if row:
                    row.active = False
                    row.rolled_back_at = datetime.utcnow()
                    db.commit()
                return

        self._MEMORY_STORE.pop(self.state_key(plugin_id, segment), None)

    @classmethod
    def reset_memory(cls) -> None:
        """
        Limpa store in-memory (testes).

        Returns:
            None
        """
        cls._MEMORY_STORE.clear()

    @classmethod
    def reset_all(cls, db: Optional[Session] = None) -> None:
        """
        Limpa promoções in-memory e registros DB (testes).

        Args:
            db: Sessão de teste opcional (preferida em pytest).

        Returns:
            None
        """
        cls.reset_memory()
        if not settings.MOBILE_EAS_UPDATE_CANARY_PERSIST_DB:
            return

        from sqlalchemy import inspect

        from app.db.session import SessionLocal

        session = db
        own_session = False
        if session is None:
            session = SessionLocal()
            own_session = True
        try:
            if "core_canary_promotions" not in inspect(session.bind).get_table_names():
                return
            session.query(CoreCanaryPromotion).delete()
            session.commit()
        finally:
            if own_session:
                session.close()

    @staticmethod
    def _row_to_dict(row: CoreCanaryPromotion) -> Dict[str, Any]:
        """
        Converte ORM em dict API-safe.

        Args:
            row: Registro CoreCanaryPromotion.

        Returns:
            Dict serializável.
        """
        return {
            "id": row.id,
            "plugin_id": row.plugin_id,
            "segment": row.segment,
            "previous_branch": row.previous_branch,
            "promoted_branch": row.promoted_branch,
            "production_channel": row.production_channel,
            "promoted": row.active,
            "active": row.active,
            "rolled_back_at": row.rolled_back_at.isoformat() if row.rolled_back_at else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
