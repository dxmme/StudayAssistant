from typing import Any
from uuid import uuid4

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base


class RefinementProposal(Base):
    __tablename__ = "refinement_proposals"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid4()))
    concept_id: Mapped[str] = mapped_column(Text, ForeignKey("concepts.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(Text, default="pending")
    cards: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    again_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    completed_at: Mapped[str | None] = mapped_column(Text, nullable=True)
