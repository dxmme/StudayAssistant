from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, Text
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CoachingSession(Base):
    __tablename__ = "coaching_sessions"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    course_id: Mapped[Optional[str]] = mapped_column(
        Text, ForeignKey("courses.id", ondelete="CASCADE")
    )
    concept_id: Mapped[Optional[str]] = mapped_column(Text, ForeignKey("concepts.id"))
    transcript: Mapped[Optional[str]] = mapped_column(Text)
    diagnostic: Mapped[Optional[Any]] = mapped_column(JSON)
    duration_min: Mapped[Optional[float]] = mapped_column(Float)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # End-of-session conclusion, generated once when the session ends.
    summary: Mapped[Optional[str]] = mapped_column(Text)
    quiz: Mapped[Optional[Any]] = mapped_column(JSON)

    __table_args__ = (
        Index("ix_coaching_sessions_course_id", "course_id"),
        Index("ix_coaching_sessions_concept_id", "concept_id"),
    )
