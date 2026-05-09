from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

DEFAULT_USER_ID = "default"
DEFAULT_AVAILABILITY: dict[str, int] = {
    "mon": 120, "tue": 120, "wed": 120,
    "thu": 120, "fri": 120, "sat": 0, "sun": 0,
}


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String(100))
    weekly_availability_minutes: Mapped[dict] = mapped_column(JSON, nullable=False)
    max_session_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
