from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, Float, ForeignKey, Integer, Text
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    course_id: Mapped[Optional[str]] = mapped_column(
        Text, ForeignKey("courses.id", ondelete="CASCADE")
    )
    concept_id: Mapped[Optional[str]] = mapped_column(Text, ForeignKey("concepts.id"))
    type: Mapped[Optional[str]] = mapped_column(Text)
    bloom_level: Mapped[Optional[int]] = mapped_column(Integer)
    question: Mapped[Optional[str]] = mapped_column(Text)
    answer: Mapped[Optional[str]] = mapped_column(Text)
    grounding: Mapped[Optional[Any]] = mapped_column(JSON)
    user_flagged: Mapped[bool] = mapped_column(Boolean, default=False)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    question_id: Mapped[Optional[str]] = mapped_column(
        Text, ForeignKey("quiz_questions.id", ondelete="CASCADE")
    )
    user_answer: Mapped[Optional[str]] = mapped_column(Text)
    score: Mapped[Optional[float]] = mapped_column(Float)
    feedback: Mapped[Optional[str]] = mapped_column(Text)
    attempted_at: Mapped[Optional[datetime]] = mapped_column(Text)
