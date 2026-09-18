from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MediaIssue(Base):
    __tablename__ = "media_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workshop_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workshops.id", ondelete="CASCADE"), nullable=False
    )
    mill_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("mills.id", ondelete="SET NULL"), nullable=True
    )
    media_type: Mapped[str] = mapped_column(String(64), nullable=False)
    qty_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    operator_name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    workshop: Mapped["Workshop"] = relationship("Workshop", back_populates="media_issues")
    mill: Mapped["Mill | None"] = relationship("Mill")
