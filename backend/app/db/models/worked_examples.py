from typing import Any, Optional

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorkedExample(Base):
    __tablename__ = "worked_examples"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    course_id: Mapped[Optional[str]] = mapped_column(
        Text, ForeignKey("courses.id", ondelete="CASCADE")
    )
    concept_id: Mapped[Optional[str]] = mapped_column(Text, ForeignKey("concepts.id"))
    title: Mapped[Optional[str]] = mapped_column(Text)
    steps: Mapped[Optional[Any]] = mapped_column(JSON)
    user_stage: Mapped[int] = mapped_column(Integer, default=0)
