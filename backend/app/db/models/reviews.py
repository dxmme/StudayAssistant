from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, Text
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (Index("ix_reviews_card_id", "card_id"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    card_id: Mapped[Optional[str]] = mapped_column(
        Text, ForeignKey("cards.id", ondelete="CASCADE")
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    rating: Mapped[Optional[int]] = mapped_column(Integer)
    elapsed_days: Mapped[Optional[float]] = mapped_column(Float)
    state_before: Mapped[Optional[Any]] = mapped_column(JSON)
    state_after: Mapped[Optional[Any]] = mapped_column(JSON)
