"""Refinement endpoint tests (unit, mocked LLM + RAG)."""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.api.refinements import get_llm_gateway, get_rag
from app.db.models.cards import Card
from app.db.models.concepts import Concept
from app.db.models.courses import Course
from app.db.models.refinement_proposals import RefinementProposal
from app.db.models.reviews import Review
from app.main import app
from app.services.llm_gateway import LLMResponse, UsageInfo


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_llm_response(cards_json: str) -> LLMResponse:
    return LLMResponse(
        text=cards_json,
        model="claude-sonnet-4-6",
        usage=UsageInfo(input_tokens=500, output_tokens=200, cache_creation_input_tokens=400, cache_read_input_tokens=0),
        stop_reason="end_turn",
    )


_CARDS_JSON = (
    '[{"question": "Was ist VC-Dim geometrisch?", "answer": "Anzahl shatter-barer Punkte.", "rationale": "Geometrische Sicht"},'
    ' {"question": "Kontrabeispiel VC-Dim?", "answer": "Kreis in R2 hat VC-Dim 3.", "rationale": "Gegenbeispiel"},'
    ' {"question": "Anwendung VC-Dim?", "answer": "Generalisierungsbounds.", "rationale": "Praxis"}]'
)


def _seed_concept(db_session, *, course: Course | None = None) -> tuple[Course, Concept]:
    if course is None:
        course = Course(id=str(uuid.uuid4()), name="StatML")
        db_session.add(course)
    concept = Concept(id=str(uuid.uuid4()), course_id=course.id, name="VC-Dimension", summary="Shattering-Zahl.")
    db_session.add(concept)
    db_session.commit()
    return course, concept


def _seed_card(db_session, concept: Concept) -> Card:
    card = Card(
        id=str(uuid.uuid4()),
        course_id=concept.course_id,
        concept_id=concept.id,
        front="Was ist VC-Dim?",
        back="d+1",
        type="basic",
        archived=False,
        review_count=0,
        lapse_count=0,
        fsrs_state={},
    )
    db_session.add(card)
    db_session.commit()
    return card


def _seed_again_reviews(db_session, card: Card, count: int, *, days_ago: int = 3) -> None:
    reviewed_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    for _ in range(count):
        db_session.add(
            Review(
                id=str(uuid.uuid4()),
                card_id=card.id,
                rating=1,
                reviewed_at=reviewed_at,
                elapsed_days=1.0,
            )
        )
    db_session.commit()


def _seed_proposal(db_session, concept: Concept, status: str = "pending") -> RefinementProposal:
    proposal = RefinementProposal(
        id=str(uuid.uuid4()),
        concept_id=concept.id,
        status=status,
        cards=[
            {"index": 0, "question": "Q0", "answer": "A0", "rationale": "R0", "card_status": "pending"},
            {"index": 1, "question": "Q1", "answer": "A1", "rationale": "R1", "card_status": "pending"},
        ],
        again_count=3,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db_session.add(proposal)
    db_session.commit()
    return proposal


# ── LLM + RAG Mocks ──────────────────────────────────────────────────────────


@pytest.fixture
def mock_llm():
    gw = MagicMock()
    gw.complete = MagicMock(return_value=_make_llm_response(_CARDS_JSON))
    return gw


@pytest.fixture
def mock_rag():
    rag = MagicMock()
    rag.search = MagicMock(return_value=[])
    return rag


@pytest.fixture
def client_with_mocks(client, mock_llm, mock_rag):
    app.dependency_overrides[get_llm_gateway] = lambda: mock_llm
    app.dependency_overrides[get_rag] = lambda: mock_rag
    yield client
    app.dependency_overrides.pop(get_llm_gateway, None)
    app.dependency_overrides.pop(get_rag, None)


# ── Tests: Refinement Status ──────────────────────────────────────────────────


def test_refinement_status_candidate(client, db_session):
    _, concept = _seed_concept(db_session)
    card = _seed_card(db_session, concept)
    _seed_again_reviews(db_session, card, count=4)

    resp = client.get(f"/api/concepts/{concept.id}/refinement-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_candidate"] is True
    assert data["again_count"] == 4
    assert data["pending_proposal_id"] is None


def test_refinement_status_not_candidate(client, db_session):
    _, concept = _seed_concept(db_session)
    card = _seed_card(db_session, concept)
    _seed_again_reviews(db_session, card, count=2)

    resp = client.get(f"/api/concepts/{concept.id}/refinement-status")
    assert resp.status_code == 200
    assert resp.json()["is_candidate"] is False


def test_refinement_status_old_ratings_ignored(client, db_session):
    _, concept = _seed_concept(db_session)
    card = _seed_card(db_session, concept)
    _seed_again_reviews(db_session, card, count=5, days_ago=20)  # older than 14 days

    resp = client.get(f"/api/concepts/{concept.id}/refinement-status")
    assert resp.status_code == 200
    assert resp.json()["is_candidate"] is False


def test_refinement_status_concept_not_found(client):
    resp = client.get("/api/concepts/nonexistent/refinement-status")
    assert resp.status_code == 404


def test_refinement_status_shows_pending_proposal_id(client, db_session):
    _, concept = _seed_concept(db_session)
    proposal = _seed_proposal(db_session, concept)

    resp = client.get(f"/api/concepts/{concept.id}/refinement-status")
    assert resp.status_code == 200
    assert resp.json()["pending_proposal_id"] == proposal.id


# ── Tests: Create Proposal ────────────────────────────────────────────────────


def test_create_proposal(client_with_mocks, db_session):
    _, concept = _seed_concept(db_session)

    resp = client_with_mocks.post(f"/api/concepts/{concept.id}/refinements")
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert len(data["cards"]) == 3
    assert all(c["card_status"] == "pending" for c in data["cards"])


def test_create_proposal_duplicate(client_with_mocks, db_session):
    _, concept = _seed_concept(db_session)
    _seed_proposal(db_session, concept)

    resp = client_with_mocks.post(f"/api/concepts/{concept.id}/refinements")
    assert resp.status_code == 400
    assert "already exists" in resp.json()["detail"]


def test_create_proposal_concept_not_found(client_with_mocks):
    resp = client_with_mocks.post("/api/concepts/nonexistent/refinements")
    assert resp.status_code == 404


def test_manual_trigger_below_threshold(client_with_mocks, db_session):
    """Manual trigger works even if again_count < AGAIN_THRESHOLD."""
    _, concept = _seed_concept(db_session)
    card = _seed_card(db_session, concept)
    _seed_again_reviews(db_session, card, count=1)

    resp = client_with_mocks.post(f"/api/concepts/{concept.id}/refinements")
    assert resp.status_code == 201


# ── Tests: List Proposals ─────────────────────────────────────────────────────


def test_list_proposals_pending(client, db_session):
    _, concept = _seed_concept(db_session)
    _seed_proposal(db_session, concept, status="pending")
    _seed_proposal(db_session, concept.__class__(
        id=str(uuid.uuid4()), course_id=concept.course_id, name="Anderes Konzept"
    ) if False else concept, status="completed")

    resp = client.get("/api/refinements?status=pending")
    assert resp.status_code == 200
    data = resp.json()
    assert all(p["status"] == "pending" for p in data)


# ── Tests: Approve / Reject ───────────────────────────────────────────────────


def test_approve_card(client, db_session):
    _, concept = _seed_concept(db_session)
    proposal = _seed_proposal(db_session, concept)

    resp = client.patch(f"/api/refinements/{proposal.id}/cards/0/approve", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["created_card_id"]

    card_entry = next(c for c in data["proposal"]["cards"] if c["index"] == 0)
    assert card_entry["card_status"] == "approved"


def test_approve_card_with_override(client, db_session):
    _, concept = _seed_concept(db_session)
    proposal = _seed_proposal(db_session, concept)

    resp = client.patch(
        f"/api/refinements/{proposal.id}/cards/0/approve",
        json={"question": "Überschriebene Frage", "answer": "Neue Antwort"},
    )
    assert resp.status_code == 200
    card_entry = next(c for c in resp.json()["proposal"]["cards"] if c["index"] == 0)
    assert card_entry["question"] == "Überschriebene Frage"
    assert card_entry["answer"] == "Neue Antwort"


def test_reject_card(client, db_session):
    _, concept = _seed_concept(db_session)
    proposal = _seed_proposal(db_session, concept)

    resp = client.patch(f"/api/refinements/{proposal.id}/cards/0/reject")
    assert resp.status_code == 200
    card_entry = next(c for c in resp.json()["proposal"]["cards"] if c["index"] == 0)
    assert card_entry["card_status"] == "rejected"


def test_proposal_completed_when_all_decided(client, db_session):
    _, concept = _seed_concept(db_session)
    proposal = _seed_proposal(db_session, concept)

    client.patch(f"/api/refinements/{proposal.id}/cards/0/approve", json={})
    resp = client.patch(f"/api/refinements/{proposal.id}/cards/1/reject")

    assert resp.json()["proposal"]["status"] == "completed"
    assert resp.json()["proposal"]["completed_at"] is not None


def test_approve_already_decided(client, db_session):
    _, concept = _seed_concept(db_session)
    proposal = _seed_proposal(db_session, concept)

    client.patch(f"/api/refinements/{proposal.id}/cards/0/approve", json={})
    resp = client.patch(f"/api/refinements/{proposal.id}/cards/0/approve", json={})
    assert resp.status_code == 409
