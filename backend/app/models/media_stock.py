from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MediaStock(Base):
    """车间研磨珠（研磨介质）库存行：同车间同介质唯一，不允许负库存。"""

    __tablename__ = "media_stocks"
    __table_args__ = (
        UniqueConstraint("workshop_id", "media_type", name="uq_media_stock_workshop_type"),
        CheckConstraint("on_hand_kg >= 0", name="ck_media_stock_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workshop_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workshops.id", ondelete="CASCADE"), nullable=False
    )
    media_type: Mapped[str] = mapped_column(String(128), nullable=False)
    on_hand_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    workshop: Mapped["Workshop"] = relationship("Workshop", back_populates="media_stocks")
