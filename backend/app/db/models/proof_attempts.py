from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import Float, ForeignKey, Integer, Text
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProofAttempt(Base):
    __tablename__ = "proof_attempts"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid4()))
    card_id: Mapped[str] = mapped_column(Text, ForeignKey("cards.id", ondelete="CASCADE"))
    turns: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    final_rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    credit_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    started_at: Mapped[str] = mapped_column(Text, nullable=False)
    finished_at: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
