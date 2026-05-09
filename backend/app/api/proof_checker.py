"""Proof Checker endpoints — POST /api/cards/{id}/proof-attempts, etc."""
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fsrs import Card as FSRSCard, Rating, Scheduler
from sqlalchemy.orm import Session

from app.api.schemas.proof_checker import (
    ApplyRatingResponse,
    ProofAttemptResponse,
    ProofTurn,
    SubmitTurnRequest,
    SubmitTurnResponse,
)
from app.db.models.cards import Card
from app.db.models.proof_attempts import ProofAttempt
from app.db.session import get_db
from app.services.llm_gateway import LLMGateway, Message

logger = logging.getLogger(__name__)
router = APIRouter(tags=["proof-checker"])

_scheduler = Scheduler()
MAX_TURNS = 5

_llm_gateway: LLMGateway | None = None


def get_llm_gateway() -> LLMGateway:
    global _llm_gateway
    if _llm_gateway is None:
        _llm_gateway = LLMGateway()
    return _llm_gateway


_SYSTEM_TEMPLATE = """\
Du bist ein strenger aber fairer Mathematik-Tutor.
Aufgabe: {question}
Referenz-Lösung (NICHT direkt zeigen): {answer}

Analysiere den Beweis-Entwurf des Users schrittweise.
Antworte NUR in einem dieser Formate:
- Falls vollständig korrekt: "Vollständig korrekt! [kurze Bestätigung]"
- Falls fehlerhaft: "Korrekt bis Schritt N. Fehler: [präzise Beschreibung]. Hinweis: [Sokrates-Frage]"

Füge am Ende deiner Antwort immer folgende Zeile an (auf einer eigenen Zeile):
STEPS_CORRECT: X, STEPS_TOTAL: Y

wobei X die Anzahl korrekter Schritte und Y die Gesamtanzahl der Beweisschritte ist."""


def _parse_steps(text: str) -> tuple[int, int]:
    m = re.search(r"STEPS_CORRECT:\s*(\d+),\s*STEPS_TOTAL:\s*(\d+)", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 0, 1


def _compute_rating(credit_score: float, turn_number: int) -> int:
    if credit_score >= 1.0:
        return 4 if turn_number <= 3 else 3
    if credit_score >= 0.5:
        return 2
    return 1


def _apply_fsrs(card: Card, rating_int: int) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    state_before = dict(card.fsrs_state) if card.fsrs_state else {}
    fsrs_card = FSRSCard.from_dict(state_before) if state_before else FSRSCard()  # type: ignore[arg-type]
    rating = Rating(rating_int)
    new_fsrs_card, _ = _scheduler.review_card(fsrs_card, rating, review_datetime=now)
    state_after: dict[str, Any] = dict(new_fsrs_card.to_dict())
    card.fsrs_state = state_after
    card.review_count = (card.review_count or 0) + 1
    if rating_int == 1:
        card.lapse_count = (card.lapse_count or 0) + 1
    return state_after


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/cards/{card_id}/proof-attempts", status_code=201, response_model=ProofAttemptResponse)
def create_attempt(
    card_id: str,
    db: Session = Depends(get_db),
) -> ProofAttemptResponse:
    card = db.get(Card, card_id)
    if card is None or card.archived:
        raise HTTPException(status_code=404, detail="Card not found")
    if not card.proof_mode:
        raise HTTPException(status_code=400, detail="Card is not in proof_mode")
    attempt = ProofAttempt(
        id=str(uuid.uuid4()),
        card_id=card_id,
        turns=[],
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return ProofAttemptResponse.model_validate(attempt)


@router.post("/proof-attempts/{attempt_id}/turns", response_model=SubmitTurnResponse)
def submit_turn(
    attempt_id: str,
    body: SubmitTurnRequest,
    db: Session = Depends(get_db),
    llm: LLMGateway = Depends(get_llm_gateway),
) -> SubmitTurnResponse:
    attempt = db.get(ProofAttempt, attempt_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found")
    if attempt.finished_at is not None:
        raise HTTPException(status_code=409, detail="Attempt already finished")

    card = db.get(Card, attempt.card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")

    turns: list[dict[str, Any]] = list(attempt.turns or [])
    turn_number = len(turns) + 1

    system_prompt = _SYSTEM_TEMPLATE.format(
        question=card.front or "",
        answer=card.back or "",
    )

    # Build message history from prior turns
    messages: list[Message] = []
    for t in turns:
        messages.append(Message(role="user", content=t["user_proof"]))
        messages.append(Message(role="assistant", content=t["llm_feedback"]))
    messages.append(Message(role="user", content=body.user_proof))

    response = llm.complete(system_prompt, messages, tier="hard", max_tokens=512)
    feedback_text = response.text

    steps_correct, steps_total = _parse_steps(feedback_text)
    is_correct = "Vollständig korrekt" in feedback_text

    turn = ProofTurn(
        turn_number=turn_number,
        user_proof=body.user_proof,
        llm_feedback=feedback_text,
        steps_correct=steps_correct,
        steps_total=steps_total,
        is_correct=is_correct,
    )
    turns.append(turn.model_dump())
    attempt.turns = turns

    is_finished = is_correct or turn_number >= MAX_TURNS
    final_rating: int | None = None
    credit_score: float | None = None
    reference_answer: str | None = None

    if is_finished:
        credit_score = steps_correct / max(steps_total, 1) if not is_correct else 1.0
        final_rating = _compute_rating(credit_score, turn_number)
        attempt.credit_score = credit_score
        attempt.final_rating = final_rating
        attempt.finished_at = datetime.now(timezone.utc).isoformat()
        reference_answer = card.back or ""

    db.commit()

    turns_remaining = max(0, MAX_TURNS - turn_number)
    return SubmitTurnResponse(
        turn=turn,
        turns_remaining=turns_remaining,
        is_finished=is_finished,
        final_rating=final_rating,
        credit_score=credit_score,
        reference_answer=reference_answer,
    )


@router.patch("/proof-attempts/{attempt_id}/apply-rating", response_model=ApplyRatingResponse)
def apply_rating(
    attempt_id: str,
    db: Session = Depends(get_db),
) -> ApplyRatingResponse:
    attempt = db.get(ProofAttempt, attempt_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found")
    if attempt.finished_at is None or attempt.final_rating is None:
        raise HTTPException(status_code=400, detail="Attempt not finished yet")

    card = db.get(Card, attempt.card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")

    state_after = _apply_fsrs(card, attempt.final_rating)
    db.commit()

    return ApplyRatingResponse(
        card_id=card.id,
        applied_rating=attempt.final_rating,
        new_fsrs_state=state_after,
    )
