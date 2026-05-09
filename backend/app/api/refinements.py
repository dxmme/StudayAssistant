import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fsrs import Card as FSRSCard
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas.refinements import (
    ApproveCardRequest,
    ApproveCardResponse,
    ProposedCard,
    RefinementCandidateItem,
    RefinementProposalResponse,
    RefinementStatusResponse,
    RejectCardResponse,
)
from app.db.models.cards import Card
from app.db.models.concepts import Concept
from app.db.models.courses import Course
from app.db.models.refinement_proposals import RefinementProposal
from app.db.models.reviews import Review
from app.db.session import get_db
from app.services.llm_gateway import LLMGateway
from app.services.rag import RAGService, get_rag_service
from app.services.refinement_engine import (
    AGAIN_THRESHOLD,
    LOOKBACK_DAYS,
    compute_again_count,
    generate_proposed_cards,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["refinements"])

_llm_gateway: LLMGateway | None = None


def get_llm_gateway() -> LLMGateway:
    global _llm_gateway
    if _llm_gateway is None:
        _llm_gateway = LLMGateway()
    return _llm_gateway


def get_rag() -> RAGService:
    return get_rag_service()


def _initial_fsrs_state(now: datetime) -> dict[str, Any]:
    card = FSRSCard()
    d: dict[str, Any] = dict(card.to_dict())
    d["due"] = now.isoformat()
    return d


def _proposal_to_response(
    proposal: RefinementProposal,
    concept_name: str | None = None,
    course_name: str | None = None,
) -> RefinementProposalResponse:
    cards = [ProposedCard(**c) for c in (proposal.cards or [])]
    return RefinementProposalResponse(
        id=proposal.id,
        concept_id=proposal.concept_id,
        concept_name=concept_name,
        course_name=course_name,
        status=proposal.status,
        cards=cards,
        again_count=proposal.again_count,
        created_at=proposal.created_at,
        completed_at=proposal.completed_at,
    )


def _load_concept_names(db: Session, proposal: RefinementProposal) -> tuple[str | None, str | None]:
    concept = db.get(Concept, proposal.concept_id)
    if concept is None:
        return None, None
    course = db.get(Course, concept.course_id) if concept.course_id else None
    return concept.name, (course.name if course else None)


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/concepts/{concept_id}/refinement-status", response_model=RefinementStatusResponse)
def get_refinement_status(concept_id: str, db: Session = Depends(get_db)) -> RefinementStatusResponse:
    concept = db.get(Concept, concept_id)
    if concept is None:
        raise HTTPException(status_code=404, detail="Concept not found")

    again_count = compute_again_count(db, concept_id)
    pending = (
        db.query(RefinementProposal)
        .filter(RefinementProposal.concept_id == concept_id, RefinementProposal.status == "pending")
        .first()
    )
    return RefinementStatusResponse(
        concept_id=concept_id,
        again_count=again_count,
        is_candidate=again_count >= AGAIN_THRESHOLD,
        pending_proposal_id=pending.id if pending else None,
    )


@router.post("/concepts/{concept_id}/refinements", status_code=201, response_model=RefinementProposalResponse)
def create_refinement(
    concept_id: str,
    db: Session = Depends(get_db),
    llm: LLMGateway = Depends(get_llm_gateway),
    rag: RAGService = Depends(get_rag),
) -> RefinementProposalResponse:
    concept = db.get(Concept, concept_id)
    if concept is None:
        raise HTTPException(status_code=404, detail="Concept not found")

    existing_pending = (
        db.query(RefinementProposal)
        .filter(RefinementProposal.concept_id == concept_id, RefinementProposal.status == "pending")
        .first()
    )
    if existing_pending:
        raise HTTPException(status_code=400, detail="Pending proposal already exists for this concept")

    existing_cards = (
        db.query(Card)
        .filter(Card.concept_id == concept_id, Card.archived == False)  # noqa: E712
        .all()
    )
    again_count = compute_again_count(db, concept_id)

    try:
        proposed = generate_proposed_cards(llm, rag, concept, existing_cards)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    now = datetime.now(UTC).isoformat()
    proposal = RefinementProposal(
        id=str(uuid.uuid4()),
        concept_id=concept_id,
        status="pending",
        cards=proposed,
        again_count=again_count,
        created_at=now,
        completed_at=None,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)

    course = db.get(Course, concept.course_id) if concept.course_id else None
    return _proposal_to_response(proposal, concept.name, course.name if course else None)


@router.get("/refinements", response_model=list[RefinementProposalResponse])
def list_refinements(
    status: str = Query(default="pending"),
    db: Session = Depends(get_db),
) -> list[RefinementProposalResponse]:
    proposals = (
        db.query(RefinementProposal).filter(RefinementProposal.status == status).all()
    )
    result = []
    for p in proposals:
        concept_name, course_name = _load_concept_names(db, p)
        result.append(_proposal_to_response(p, concept_name, course_name))
    return result


@router.patch(
    "/refinements/{proposal_id}/cards/{card_index}/approve",
    response_model=ApproveCardResponse,
)
def approve_card(
    proposal_id: str,
    card_index: int,
    body: ApproveCardRequest,
    db: Session = Depends(get_db),
) -> ApproveCardResponse:
    proposal = db.get(RefinementProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")

    cards: list[dict[str, Any]] = list(proposal.cards or [])
    card_entry = next((c for c in cards if c["index"] == card_index), None)
    if card_entry is None:
        raise HTTPException(status_code=404, detail="Card not found in proposal")
    if card_entry["card_status"] in ("approved", "rejected"):
        raise HTTPException(status_code=409, detail="Card already approved or rejected")

    concept = db.get(Concept, proposal.concept_id)

    question = body.question if body.question is not None else card_entry["question"]
    answer = body.answer if body.answer is not None else card_entry["answer"]

    now = datetime.now(UTC)
    new_card = Card(
        id=str(uuid.uuid4()),
        course_id=concept.course_id if concept else None,
        concept_id=proposal.concept_id,
        type="basic",
        front=question,
        back=answer,
        fsrs_state=_initial_fsrs_state(now),
        review_count=0,
        lapse_count=0,
        created_at=now,
        archived=False,
    )
    db.add(new_card)

    updated_cards = [dict(c) for c in cards]
    for c in updated_cards:
        if c["index"] == card_index:
            c["card_status"] = "approved"
            c["question"] = question
            c["answer"] = answer
    proposal.cards = updated_cards
    _maybe_complete(proposal, updated_cards, now)

    db.commit()
    db.refresh(proposal)

    concept_name, course_name = _load_concept_names(db, proposal)
    return ApproveCardResponse(
        created_card_id=new_card.id,
        proposal=_proposal_to_response(proposal, concept_name, course_name),
    )


@router.patch(
    "/refinements/{proposal_id}/cards/{card_index}/reject",
    response_model=RejectCardResponse,
)
def reject_card(
    proposal_id: str,
    card_index: int,
    db: Session = Depends(get_db),
) -> RejectCardResponse:
    proposal = db.get(RefinementProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")

    cards: list[dict[str, Any]] = list(proposal.cards or [])
    card_entry = next((c for c in cards if c["index"] == card_index), None)
    if card_entry is None:
        raise HTTPException(status_code=404, detail="Card not found in proposal")
    if card_entry["card_status"] in ("approved", "rejected"):
        raise HTTPException(status_code=409, detail="Card already approved or rejected")

    updated_cards = [dict(c) for c in cards]
    for c in updated_cards:
        if c["index"] == card_index:
            c["card_status"] = "rejected"
    proposal.cards = updated_cards
    now = datetime.now(UTC)
    _maybe_complete(proposal, updated_cards, now)

    db.commit()
    db.refresh(proposal)

    concept_name, course_name = _load_concept_names(db, proposal)
    return RejectCardResponse(proposal=_proposal_to_response(proposal, concept_name, course_name))


@router.get("/courses/{course_id}/refinement-candidates", response_model=list[RefinementCandidateItem])
def list_refinement_candidates(
    course_id: str,
    db: Session = Depends(get_db),
) -> list[RefinementCandidateItem]:
    from datetime import timedelta

    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")

    cutoff = datetime.now(UTC) - timedelta(days=LOOKBACK_DAYS)
    rows = db.execute(
        select(Card.concept_id, func.count(Review.id).label("again_count"))
        .join(Review, Card.id == Review.card_id)
        .where(
            Card.course_id == course_id,
            Card.concept_id.is_not(None),
            Review.rating == 1,
            Review.reviewed_at >= cutoff,
        )
        .group_by(Card.concept_id)
        .having(func.count(Review.id) >= AGAIN_THRESHOLD)
    ).all()
    return [RefinementCandidateItem(concept_id=row[0], again_count=row[1]) for row in rows]


def _maybe_complete(proposal: RefinementProposal, cards: list[dict[str, Any]], now: datetime) -> None:
    all_decided = all(c["card_status"] in ("approved", "rejected") for c in cards)
    if all_decided:
        proposal.status = "completed"
        proposal.completed_at = now.isoformat()
