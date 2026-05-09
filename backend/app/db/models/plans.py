from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import Date, ForeignKey, Integer, Text
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlanSession(Base):
    __tablename__ = "plan_sessions"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    course_id: Mapped[Optional[str]] = mapped_column(
        Text, ForeignKey("courses.id", ondelete="CASCADE")
    )
    scheduled_date: Mapped[Optional[date]] = mapped_column(Date)
    duration_min: Mapped[Optional[int]] = mapped_column(Integer)
    items: Mapped[Optional[Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(Text, default="pending")
    completed_at: Mapped[Optional[datetime]] = mapped_column(Text)
