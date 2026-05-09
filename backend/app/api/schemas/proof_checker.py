from typing import Any, Optional

from pydantic import BaseModel


class ProofAttemptCreate(BaseModel):
    pass


class ProofTurn(BaseModel):
    turn_number: int
    user_proof: str
    llm_feedback: str
    steps_correct: int
    steps_total: int
    is_correct: bool


class ProofAttemptResponse(BaseModel):
    id: str
    card_id: str
    turns: list[Any]
    final_rating: Optional[int]
    credit_score: Optional[float]
    started_at: str
    finished_at: Optional[str]

    model_config = {"from_attributes": True}


class SubmitTurnRequest(BaseModel):
    user_proof: str


class SubmitTurnResponse(BaseModel):
    turn: ProofTurn
    turns_remaining: int
    is_finished: bool
    final_rating: Optional[int] = None
    credit_score: Optional[float] = None
    reference_answer: Optional[str] = None


class ApplyRatingResponse(BaseModel):
    card_id: str
    applied_rating: int
    new_fsrs_state: dict[str, Any]
