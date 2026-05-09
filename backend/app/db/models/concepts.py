from typing import Any, Optional

from sqlalchemy import Float, ForeignKey, Integer, PrimaryKeyConstraint, Text
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Concept(Base):
    __tablename__ = "concepts"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    course_id: Mapped[Optional[str]] = mapped_column(
        Text, ForeignKey("courses.id", ondelete="CASCADE")
    )
    name: Mapped[Optional[str]] = mapped_column(Text)
    type: Mapped[Optional[str]] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    target_bloom: Mapped[Optional[int]] = mapped_column(Integer)
    importance: Mapped[Optional[float]] = mapped_column(Float)
    prerequisites: Mapped[Optional[Any]] = mapped_column(JSON)
    source_pages: Mapped[Optional[Any]] = mapped_column(JSON)


class ConceptEdge(Base):
    __tablename__ = "concept_edges"
    __table_args__ = (PrimaryKeyConstraint("src", "dst", "relation"),)

    src: Mapped[str] = mapped_column(Text, ForeignKey("concepts.id", ondelete="CASCADE"))
    dst: Mapped[str] = mapped_column(Text, ForeignKey("concepts.id"))
    relation: Mapped[str] = mapped_column(Text)
