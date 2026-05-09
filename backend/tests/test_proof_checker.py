"""Proof Checker endpoint tests (unit, mocked LLM)."""
import uuid
from unittest.mock import MagicMock

import pytest

from app.api.proof_checker import get_llm_gateway
from app.db.models.cards import Card
from app.db.models.courses import Course
from app.db.models.proof_attempts import ProofAttempt
from app.main import app
from app.services.llm_gateway import LLMResponse, UsageInfo


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_llm_response(text: str) -> LLMResponse:
    return LLMResponse(
        text=text,
        model="claude-opus-4-7",
        usage=UsageInfo(
            input_tokens=400,
            output_tokens=200,
            cache_creation_input_tokens=300,
            cache_read_input_tokens=0,
        ),
        stop_reason="end_turn",
    )


def _seed_card(db_session, *, proof_mode: bool = True, archived: bool = False) -> tuple[Course, Card]:
    course = Course(id=str(uuid.uuid4()), name="StatML")
    card = Card(
        id=str(uuid.uuid4()),
        course_id=course.id,
        front="Zeige, dass die VC-Dim. des Halbraums in ℝᵈ gleich d+1 ist.",
        back="Sei S = {e_1,...,e_{d+1}}. Es lässt sich zeigen, dass ...",
        proof_mode=proof_mode,
        archived=archived,
        review_count=0,
        lapse_count=0,
        fsrs_state={"card_id": 1, "state": 2, "step": 0, "stability": 1.0, "difficulty": 5.0, "due": "2026-01-01T00:00:00", "last_review": None},
    )
    db_session.add_all([course, card])
    db_session.commit()
    return course, card


FEEDBACK_PARTIAL = (
    "Korrekt bis Schritt 2. Fehler: Die Unabhängigkeit wurde nicht begründet. "
    "Hinweis: Welche Eigenschaft garantiert lineare Unabhängigkeit?\n"
    "STEPS_CORRECT: 2, STEPS_TOTAL: 4"
)
FEEDBACK_CORRECT = "Vollständig korrekt! Sehr gut strukturierter Beweis.\nSTEPS_CORRECT: 4, STEPS_TOTAL: 4"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_llm_partial():
    gateway = MagicMock()
    gateway.calls: list[dict] = []

    def complete(system, messages, tier="default", max_tokens=512):
        gateway.calls.append({"system": system, "messages": list(messages), "tier": tier})
        return _make_llm_response(FEEDBACK_PARTIAL)

    gateway.complete = complete
    return gateway


@pytest.fixture
def mock_llm_correct():
    gateway = MagicMock()

    def complete(system, messages, tier="default", max_tokens=512):
        return _make_llm_response(FEEDBACK_CORRECT)

    gateway.complete = complete
    return gateway


@pytest.fixture
def pc_client_partial(client, mock_llm_partial):
    app.dependency_overrides[get_llm_gateway] = lambda: mock_llm_partial
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def pc_client_correct(client, mock_llm_correct):
    app.dependency_overrides[get_llm_gateway] = lambda: mock_llm_correct
    yield client
    app.dependency_overrides.clear()


# ── Tests: create_attempt ─────────────────────────────────────────────────────


def test_create_attempt(client, db_session):
    _, card = _seed_card(db_session, proof_mode=True)
    r = client.post(f"/api/cards/{card.id}/proof-attempts")
    assert r.status_code == 201
    data = r.json()
    assert data["card_id"] == card.id
    assert data["turns"] == []
    assert data["final_rating"] is None


def test_create_attempt_non_proof_card(client, db_session):
    _, card = _seed_card(db_session, proof_mode=False)
    r = client.post(f"/api/cards/{card.id}/proof-attempts")
    assert r.status_code == 400
    assert "proof_mode" in r.json()["detail"]


def test_create_attempt_card_not_found(client):
    r = client.post("/api/cards/nonexistent/proof-attempts")
    assert r.status_code == 404


# ── Tests: submit_turn ────────────────────────────────────────────────────────


def test_submit_turn_feedback(pc_client_partial, db_session):
    _, card = _seed_card(db_session)
    attempt_id = pc_client_partial.post(f"/api/cards/{card.id}/proof-attempts").json()["id"]

    r = pc_client_partial.post(
        f"/api/proof-attempts/{attempt_id}/turns",
        json={"user_proof": "Sei n ∈ ℕ..."},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["turn"]["turn_number"] == 1
    assert data["turns_remaining"] == 4
    assert data["is_finished"] is False
    assert data["final_rating"] is None


def test_submit_turn_correct_proof(pc_client_correct, db_session):
    _, card = _seed_card(db_session)
    attempt_id = pc_client_correct.post(f"/api/cards/{card.id}/proof-attempts").json()["id"]

    r = pc_client_correct.post(
        f"/api/proof-attempts/{attempt_id}/turns",
        json={"user_proof": "Vollständiger Beweis..."},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["is_finished"] is True
    assert data["final_rating"] == 4  # Turn 1 ≤ 3, score = 1.0
    assert data["reference_answer"] is not None


def test_submit_turn_max_turns_exceeded(pc_client_partial, db_session):
    _, card = _seed_card(db_session)
    attempt_id = pc_client_partial.post(f"/api/cards/{card.id}/proof-attempts").json()["id"]

    for _ in range(5):
        pc_client_partial.post(
            f"/api/proof-attempts/{attempt_id}/turns",
            json={"user_proof": "Versuch..."},
        )

    r = pc_client_partial.post(
        f"/api/proof-attempts/{attempt_id}/turns",
        json={"user_proof": "Noch ein Versuch..."},
    )
    assert r.status_code == 409


def test_submit_turn_parse_steps(pc_client_partial, db_session):
    _, card = _seed_card(db_session)
    attempt_id = pc_client_partial.post(f"/api/cards/{card.id}/proof-attempts").json()["id"]

    # Submit all 5 turns to finish and get credit_score
    for _ in range(4):
        pc_client_partial.post(
            f"/api/proof-attempts/{attempt_id}/turns",
            json={"user_proof": "Versuch..."},
        )
    r = pc_client_partial.post(
        f"/api/proof-attempts/{attempt_id}/turns",
        json={"user_proof": "Letzter Versuch..."},
    )
    data = r.json()
    assert data["is_finished"] is True
    # STEPS_CORRECT: 2, STEPS_TOTAL: 4 → credit_score ≈ 0.5 → Rating 2
    assert abs(data["credit_score"] - 0.5) < 0.01
    assert data["final_rating"] == 2


def test_partial_credit_scoring(pc_client_partial, db_session):
    # credit_score = 0.5 → rating 2 (tested in test_submit_turn_parse_steps)
    # credit_score = 1.0 turn≤3 → rating 4 (tested in test_submit_turn_correct_proof)
    pass


def test_attempt_history_persisted(pc_client_partial, db_session):
    _, card = _seed_card(db_session)
    attempt_id = pc_client_partial.post(f"/api/cards/{card.id}/proof-attempts").json()["id"]

    pc_client_partial.post(
        f"/api/proof-attempts/{attempt_id}/turns",
        json={"user_proof": "Erster Beweis..."},
    )

    attempt = db_session.get(ProofAttempt, attempt_id)
    db_session.refresh(attempt)
    assert len(attempt.turns) == 1
    assert attempt.turns[0]["turn_number"] == 1


# ── Tests: apply_rating ───────────────────────────────────────────────────────


def test_apply_rating_updates_fsrs(pc_client_correct, db_session):
    _, card = _seed_card(db_session)
    attempt_id = pc_client_correct.post(f"/api/cards/{card.id}/proof-attempts").json()["id"]

    pc_client_correct.post(
        f"/api/proof-attempts/{attempt_id}/turns",
        json={"user_proof": "Korrekter Beweis..."},
    )

    r = pc_client_correct.patch(f"/api/proof-attempts/{attempt_id}/apply-rating")
    assert r.status_code == 200
    data = r.json()
    assert data["card_id"] == card.id
    assert data["applied_rating"] == 4
    assert "new_fsrs_state" in data


def test_apply_rating_not_finished(client, db_session):
    _, card = _seed_card(db_session)
    attempt_id = client.post(f"/api/cards/{card.id}/proof-attempts").json()["id"]

    r = client.patch(f"/api/proof-attempts/{attempt_id}/apply-rating")
    assert r.status_code == 400
    assert "not finished" in r.json()["detail"]
