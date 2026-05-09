from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Float, ForeignKey, Integer, Text
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MockExam(Base):
    __tablename__ = "mock_exams"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    course_id: Mapped[Optional[str]] = mapped_column(
        Text, ForeignKey("courses.id", ondelete="CASCADE")
    )
    based_on: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[datetime]] = mapped_column(Text)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(Text)
    duration_min: Mapped[Optional[int]] = mapped_column(Integer)
    answers: Mapped[Optional[Any]] = mapped_column(JSON)
    score: Mapped[Optional[float]] = mapped_column(Float)
    breakdown: Mapped[Optional[Any]] = mapped_column(JSON)
