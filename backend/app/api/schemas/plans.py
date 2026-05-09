from datetime import date
from typing import Literal

from pydantic import BaseModel


class PlanItem(BaseModel):
    model_config = {"from_attributes": True}

    type: Literal["card_review", "new_concept", "coaching"]
    title: str
    estimated_min: int
    done: bool = False
    concept_id: str | None = None
    card_count: int | None = None


class PlanSessionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    course_id: str | None
    scheduled_date: date | None
    duration_min: int | None
    items: list[PlanItem]
    status: str
    completed_at: str | None
