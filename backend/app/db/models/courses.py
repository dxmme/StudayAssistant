from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    semester: Mapped[Optional[str]] = mapped_column(Text)
    exam_date: Mapped[Optional[date]] = mapped_column(Date)
    exam_format: Mapped[Optional[str]] = mapped_column(Text)
    professor: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
