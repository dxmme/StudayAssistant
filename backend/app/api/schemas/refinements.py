from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProposedCard(BaseModel):
    index: int
    question: str
    answer: str
    rationale: str
    card_status: str  # 'pending' | 'approved' | 'rejected'


class RefinementStatusResponse(BaseModel):
    concept_id: str
    again_count: int
    is_candidate: bool
    pending_proposal_id: Optional[str] = None


class RefinementProposalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    concept_id: str
    concept_name: Optional[str] = None
    course_name: Optional[str] = None
    status: str
    cards: list[ProposedCard]
    again_count: Optional[int] = None
    created_at: str
    completed_at: Optional[str] = None


class ApproveCardRequest(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None


class ApproveCardResponse(BaseModel):
    created_card_id: str
    proposal: RefinementProposalResponse


class RejectCardResponse(BaseModel):
    proposal: RefinementProposalResponse


class RefinementCandidateItem(BaseModel):
    concept_id: str
    again_count: int
