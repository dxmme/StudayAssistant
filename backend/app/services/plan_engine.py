import uuid
from datetime import date
from typing import cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.cards import Card
from app.db.models.concepts import Concept, ConceptEdge
from app.db.models.courses import Course
from app.db.models.plans import PlanSession
from app.db.models.user_preferences import UserPreferences

CARD_REVIEW_MIN_PER_CARD = 2
NEW_CONCEPT_MIN = 10
COACHING_MIN = 15
MAX_CARDS_IN_REVIEW = 30
MASTERY_STABILITY_THRESHOLD = 21.0


def _determine_phase(exam_date: date | None, today: date) -> str:
    if exam_date is None:
        return "semester_companion"
    days = (exam_date - today).days
    if days > 42:
        return "semester_companion"
    if days > 14:
        return "active_preparation"
    if days > 3:
        return "consolidation"
    return "final_review"


def _is_mastered(concept_id: str, db: Session) -> bool:
    cards = db.scalars(
        select(Card).where(Card.concept_id == concept_id, Card.archived == False)  # noqa: E712
    ).all()
    if not cards:
        return False
    stabilities: list[float] = [
        float(c.fsrs_state.get("stability", 0)) for c in cards if c.fsrs_state
    ]
    if not stabilities:
        return False
    return bool((sum(stabilities) / len(stabilities)) >= MASTERY_STABILITY_THRESHOLD)


def _pick_next_concept(course_id: str, db: Session) -> Concept | None:
    concepts = db.scalars(
        select(Concept).where(Concept.course_id == course_id)
    ).all()
    if not concepts:
        return None

    mastered_ids = {c.id for c in concepts if _is_mastered(c.id, db)}

    def prereqs_done(concept: Concept) -> bool:
        edges = db.scalars(
            select(ConceptEdge).where(
                ConceptEdge.dst == concept.id,
                ConceptEdge.relation == "prerequisite",
            )
        ).all()
        return {str(e.src) for e in edges}.issubset(mastered_ids)

    candidates = [c for c in concepts if c.id not in mastered_ids and prereqs_done(c)]
    if not candidates:
        return None
    candidates.sort(key=lambda c: c.importance or 0.0, reverse=True)
    return candidates[0]


def generate_plan(course_id: str, db: Session) -> tuple[PlanSession, bool]:
    today = date.today()

    existing = db.scalars(
        select(PlanSession).where(
            PlanSession.course_id == course_id,
            PlanSession.scheduled_date == today,
        )
    ).first()
    if existing:
        return existing, False

    course = db.get(Course, course_id)
    if course is None:
        raise ValueError("course_not_found")

    prefs = db.scalars(select(UserPreferences)).first()
    budget = prefs.max_session_minutes if prefs else 90

    phase = _determine_phase(course.exam_date, today)

    all_cards = db.scalars(
        select(Card).where(Card.course_id == course_id, Card.archived == False)  # noqa: E712
    ).all()
    today_iso = today.isoformat()
    due_cards = [
        c for c in all_cards
        if c.fsrs_state and c.fsrs_state.get("due", "9999") <= today_iso
    ]

    items: list[dict[str, object]] = []

    if due_cards:
        count = min(len(due_cards), MAX_CARDS_IN_REVIEW)
        est = count * CARD_REVIEW_MIN_PER_CARD
        items.append({
            "type": "card_review",
            "title": f"{count} fällige Karten",
            "estimated_min": est,
            "done": False,
            "concept_id": None,
            "card_count": count,
        })
        budget -= est

    if phase in ("semester_companion", "active_preparation") and budget >= NEW_CONCEPT_MIN:
        concept = _pick_next_concept(course_id, db)
        if concept:
            items.append({
                "type": "new_concept",
                "title": concept.name or "Unbekanntes Konzept",
                "estimated_min": NEW_CONCEPT_MIN,
                "done": False,
                "concept_id": concept.id,
                "card_count": None,
            })
            budget -= NEW_CONCEPT_MIN

            if budget >= COACHING_MIN:
                items.append({
                    "type": "coaching",
                    "title": f"Coaching: {concept.name or 'Konzept'}",
                    "estimated_min": COACHING_MIN,
                    "done": False,
                    "concept_id": concept.id,
                    "card_count": None,
                })

    duration = sum(cast(int, i["estimated_min"]) for i in items)
    plan = PlanSession(
        id=str(uuid.uuid4()),
        course_id=course_id,
        scheduled_date=today,
        duration_min=duration,
        items=items,
        status="pending",
        completed_at=None,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan, True
