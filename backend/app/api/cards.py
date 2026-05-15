import logging
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fsrs import Card as FSRSCard
from fsrs import Rating, Scheduler
from sqlalchemy.orm import Session

from app.api.schemas.cards import CardCreate, CardResponse, CardUpdate, ReviewRequest, ReviewResponse
from app.db.models.cards import Card
from app.db.models.concepts import Concept
from app.db.models.reviews import Review
from app.db.session import get_db
from app.services import card_generator as card_gen_svc
from app.services.rag import get_rag_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["cards"])

_scheduler = Scheduler()

VALID_CARD_TYPES = {"basic", "cloze", "concept_diagram", "derivation", "proof_skeleton"}


def _initial_fsrs_state(now: datetime) -> dict:
    card = FSRSCard()
    d = card.to_dict()
    # Override due to created_at so card is immediately reviewable
    d["due"] = now.isoformat()
    return d


def _card_to_response(card: Card) -> CardResponse:
    return CardResponse.model_validate(card)


# ── Card CRUD ─────────────────────────────────────────────────────────────────

@router.post("/courses/{course_id}/cards", status_code=201, response_model=CardResponse)
def create_card(
    course_id: str,
    body: CardCreate,
    db: Session = Depends(get_db),
) -> CardResponse:
    now = datetime.now(timezone.utc)
    card = Card(
        id=str(uuid.uuid4()),
        course_id=course_id,
        concept_id=body.concept_id,
        type=body.type,
        front=body.front,
        back=body.back,
        bloom_level=body.bloom_level,
        fsrs_state=_initial_fsrs_state(now),
        review_count=0,
        lapse_count=0,
        created_at=now,
        archived=False,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return _card_to_response(card)


@router.get("/cards/{card_id}", response_model=CardResponse)
def get_card(card_id: str, db: Session = Depends(get_db)) -> CardResponse:
    card = db.get(Card, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return _card_to_response(card)


@router.patch("/cards/{card_id}", response_model=CardResponse)
def update_card(
    card_id: str,
    body: CardUpdate,
    db: Session = Depends(get_db),
) -> CardResponse:
    card = db.get(Card, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(card, field, value)
    db.commit()
    db.refresh(card)
    return _card_to_response(card)


@router.delete("/cards/{card_id}", status_code=204)
def delete_card(card_id: str, db: Session = Depends(get_db)) -> None:
    card = db.get(Card, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    card.archived = True
    db.commit()


@router.get("/courses/{course_id}/cards", response_model=list[CardResponse])
def list_cards(
    course_id: str,
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[CardResponse]:
    q = db.query(Card).filter(Card.course_id == course_id)
    if not include_archived:
        q = q.filter(Card.archived == False)  # noqa: E712
    return [_card_to_response(c) for c in q.all()]


@router.post("/courses/{course_id}/cards/generate-missing")
def generate_missing_cards(
    course_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Generate cards for concepts that don't have any yet."""
    rag = get_rag_service()

    # Find concepts without cards
    concepts_with_cards = db.query(Card.concept_id).filter(
        Card.course_id == course_id,
        Card.archived == False,  # noqa: E712
    ).distinct()

    concepts_without_cards = db.query(Concept).filter(
        Concept.course_id == course_id,
        ~Concept.id.in_(concepts_with_cards),
    ).all()

    generated = 0
    errors = 0

    for concept in concepts_without_cards:
        try:
            card = card_gen_svc.generate_card_for_concept(concept, db, rag)
            db.add(card)
            generated += 1
        except Exception as exc:
            logger.warning(
                "generate_missing_card_failed",
                extra={"concept_id": concept.id, "error": str(exc)},
            )
            errors += 1

    db.commit()

    # Total counts
    total_concepts = db.query(Concept).filter(Concept.course_id == course_id).count()
    total_cards = db.query(Card).filter(
        Card.course_id == course_id,
        Card.archived == False,  # noqa: E712
    ).count()

    return {
        "generated": generated,
        "already_exist": total_cards - generated,
        "errors": errors,
        "total_concepts": total_concepts,
        "total_cards": total_cards,
    }


@router.get("/courses/{course_id}/cards/due", response_model=list[CardResponse])
def get_due_cards(
    course_id: str,
    on: Optional[str] = Query(default=None, description="Date YYYY-MM-DD, default today UTC"),
    db: Session = Depends(get_db),
) -> list[CardResponse]:
    if on:
        cutoff = datetime.combine(date.fromisoformat(on), datetime.max.time()).replace(
            tzinfo=timezone.utc
        )
    else:
        today = datetime.now(timezone.utc).date()
        cutoff = datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc)

    cards = (
        db.query(Card)
        .filter(Card.course_id == course_id, Card.archived == False)  # noqa: E712
        .all()
    )

    due_cards = []
    for card in cards:
        if not card.fsrs_state:
            continue
        due_str = card.fsrs_state.get("due")
        if not due_str:
            continue
        due_dt = datetime.fromisoformat(due_str)
        if due_dt.tzinfo is None:
            due_dt = due_dt.replace(tzinfo=timezone.utc)
        if due_dt <= cutoff:
            due_cards.append(card)

    due_cards.sort(key=lambda c: c.fsrs_state.get("due", "") if c.fsrs_state else "")
    return [_card_to_response(c) for c in due_cards]


# ── Review ────────────────────────────────────────────────────────────────────

@router.post("/cards/{card_id}/review", response_model=ReviewResponse)
def review_card(
    card_id: str,
    body: ReviewRequest,
    db: Session = Depends(get_db),
) -> ReviewResponse:
    card = db.get(Card, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    if card.archived:
        raise HTTPException(status_code=409, detail="Cannot review archived card")

    review_dt = body.reviewed_at or datetime.now(timezone.utc)
    if review_dt.tzinfo is None:
        review_dt = review_dt.replace(tzinfo=timezone.utc)

    state_before = dict(card.fsrs_state) if card.fsrs_state else {}

    # Reconstruct fsrs.Card from stored state
    fsrs_card = FSRSCard.from_dict(state_before) if state_before else FSRSCard()

    # elapsed_days: days since last review (0 for first review)
    elapsed_days: float = 0.0
    last_review_str = state_before.get("last_review")
    if last_review_str:
        last_review_dt = datetime.fromisoformat(last_review_str)
        if last_review_dt.tzinfo is None:
            last_review_dt = last_review_dt.replace(tzinfo=timezone.utc)
        elapsed_days = max(0.0, (review_dt - last_review_dt).total_seconds() / 86400)

    rating = Rating(body.rating)
    new_fsrs_card, _ = _scheduler.review_card(fsrs_card, rating, review_datetime=review_dt)
    state_after = new_fsrs_card.to_dict()

    # Write review row
    review = Review(
        id=str(uuid.uuid4()),
        card_id=card_id,
        reviewed_at=review_dt,
        rating=body.rating,
        elapsed_days=elapsed_days,
        state_before=state_before,
        state_after=state_after,
    )
    db.add(review)

    # Update card
    card.fsrs_state = state_after
    card.review_count = (card.review_count or 0) + 1
    if body.rating == 1:
        card.lapse_count = (card.lapse_count or 0) + 1

    db.commit()
    db.refresh(card)

    logger.info(
        "card_reviewed",
        extra={
            "card_id": card_id,
            "rating": body.rating,
            "elapsed_days": elapsed_days,
            "stability_before": state_before.get("stability"),
            "stability_after": state_after.get("stability"),
            "due_after": state_after.get("due"),
        },
    )

    return ReviewResponse(
        card_id=card_id,
        fsrs_state=state_after,
        next_due=state_after.get("due", ""),
        lapse_count=card.lapse_count,
        review_count=card.review_count,
    )
