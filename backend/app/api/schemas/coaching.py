from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class CoachingSessionCreate(BaseModel):
    course_id: str
    concept_id: str
    target_bloom: Optional[int] = Field(default=None, ge=1, le=6)


class CoachingSessionCreated(BaseModel):
    session_id: str
    started_at: datetime


class CoachingTurnRequest(BaseModel):
    user_message: str


class QuizQuestion(BaseModel):
    question: str
    options: list[str]
    correct_index: int
    explanation: str


class CoachingSessionEnded(BaseModel):
    session_id: str
    duration_min: float
    turn_count: int
    summary: Optional[str] = None
    quiz: list[QuizQuestion] = []


class CoachingSessionResponse(BaseModel):
    id: str
    course_id: Optional[str]
    concept_id: Optional[str]
    transcript: Optional[str]
    started_at: Optional[datetime]
    duration_min: Optional[float]
    diagnostic: Optional[Any]
    summary: Optional[str] = None
    quiz: Optional[list[QuizQuestion]] = None

    model_config = {"from_attributes": True}


class CoachingSessionListItem(BaseModel):
    id: str
    concept_id: Optional[str]
    started_at: Optional[datetime]
    duration_min: Optional[float]

    model_config = {"from_attributes": True}
