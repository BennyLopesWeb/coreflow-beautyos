"""
CoreCanaryPromotion — promoções canary ativas persistidas (CF-25).

Permite rollback automático sobreviver a restart do worker/API.
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.db.base import Base


class CoreCanaryPromotion(Base):
    """
    Registro persistente de promoção canary → production.

    Attributes:
        id: Identificador interno.
        plugin_id: Plugin vertical (beauty, sports, clinic).
        segment: Segmento de mercado canary.
        previous_branch: Branch production antes da promoção.
        promoted_branch: Branch canary promovido.
        production_channel: Channel EAS production afetado.
        active: True enquanto aguardando monitoramento/rollback.
        rolled_back_at: Timestamp se rollback já executado.
        created_at: Quando a promoção foi registrada.
    """

    __tablename__ = "core_canary_promotions"
    __table_args__ = (
        UniqueConstraint("plugin_id", "segment", name="uq_canary_promotion_plugin_segment"),
    )

    id = Column(Integer, primary_key=True, index=True)
    plugin_id = Column(String, nullable=False, index=True)
    segment = Column(String, nullable=False, index=True)
    previous_branch = Column(String, nullable=False)
    promoted_branch = Column(String, nullable=False)
    production_channel = Column(String, nullable=False)
    active = Column(Boolean, default=True, nullable=False, index=True)
    rolled_back_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
