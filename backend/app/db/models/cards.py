from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Card(Base):
    __tablename__ = "cards"
    __table_args__ = (Index("ix_cards_course_archived", "course_id", "archived"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    course_id: Mapped[Optional[str]] = mapped_column(
        Text, ForeignKey("courses.id", ondelete="CASCADE")
    )
    concept_id: Mapped[Optional[str]] = mapped_column(Text, ForeignKey("concepts.id"))
    type: Mapped[Optional[str]] = mapped_column(Text)
    front: Mapped[Optional[str]] = mapped_column(Text)
    back: Mapped[Optional[str]] = mapped_column(Text)
    bloom_level: Mapped[Optional[int]] = mapped_column(Integer)
    fsrs_state: Mapped[Optional[Any]] = mapped_column(JSON)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    lapse_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
