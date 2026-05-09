from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel

CardType = Literal["basic", "cloze", "concept_diagram", "derivation", "proof_skeleton"]

# fsrs.Card.to_dict() schema — stored as-is in DB
# Keys: card_id, state (int 1=Learning 2=Review 3=Relearning), step, stability, difficulty,
#       due (ISO8601), last_review (ISO8601 or null)
FSRSStateDict = dict[str, Any]


class CardCreate(BaseModel):
    type: CardType
    front: str
    back: str
    bloom_level: Optional[int] = None
    concept_id: Optional[str] = None


class CardUpdate(BaseModel):
    type: Optional[CardType] = None
    front: Optional[str] = None
    back: Optional[str] = None
    bloom_level: Optional[int] = None
    concept_id: Optional[str] = None
    archived: Optional[bool] = None


class CardResponse(BaseModel):
    id: str
    course_id: Optional[str]
    concept_id: Optional[str]
    type: Optional[str]
    front: Optional[str]
    back: Optional[str]
    bloom_level: Optional[int]
    fsrs_state: Optional[FSRSStateDict]
    review_count: int
    lapse_count: int
    created_at: Optional[datetime]
    archived: bool

    model_config = {"from_attributes": True}


class ReviewRequest(BaseModel):
    rating: Literal[1, 2, 3, 4]
    reviewed_at: Optional[datetime] = None


class ReviewResponse(BaseModel):
    card_id: str
    fsrs_state: FSRSStateDict
    next_due: str
    lapse_count: int
    review_count: int
