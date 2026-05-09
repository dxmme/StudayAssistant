"""Worked-examples endpoint tests (unit, mocked LLM + RAG)."""
import uuid
from unittest.mock import MagicMock

import pytest

from app.api.worked_examples import get_llm_gateway, get_rag
from app.db.models.cards import Card
from app.db.models.courses import Course
from app.main import app
from app.services.llm_gateway import LLMResponse, UsageInfo


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_llm_response(text: str = "## Worked Example\n\n**Problem:** ...") -> LLMResponse:
    return LLMResponse(
        text=text,
        model="claude-opus-4-7",
        usage=UsageInfo(
            input_tokens=500,
            output_tokens=300,
            cache_creation_input_tokens=400,
            cache_read_input_tokens=0,
        ),
        stop_reason="end_turn",
    )


def _seed_card(db_session, *, archived: bool = False) -> tuple[Course, Card]:
    course = Course(id=str(uuid.uuid4()), name="StatML")
    card = Card(
        id=str(uuid.uuid4()),
        course_id=course.id,
        front="Was ist die VC-Dimension des Halbraums in ℝᵈ?",
        back="d+1",
        archived=archived,
        review_count=0,
        lapse_count=0,
        fsrs_state={},
    )
    db_session.add_all([course, card])
    db_session.commit()
    return course, card


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_llm():
    gateway = MagicMock()
    gateway.calls: list[dict] = []

    def complete(system, messages, tier="default", cache_breakpoints=None, max_tokens=1024):
        gateway.calls.append({"system": system, "messages": list(messages), "tier": tier})
        return _make_llm_response()

    gateway.complete = complete
    return gateway


@pytest.fixture
def mock_rag():
    rag = MagicMock()
    rag.search = MagicMock(return_value=[])
    return rag


@pytest.fixture
def we_client(client, mock_llm, mock_rag):
    app.dependency_overrides[get_llm_gateway] = lambda: mock_llm
    app.dependency_overrides[get_rag] = lambda: mock_rag
    yield client
    app.dependency_overrides.clear()


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_worked_example_returns_content(we_client, db_session):
    _, card = _seed_card(db_session)
    r = we_client.post(f"/api/cards/{card.id}/worked-example")
    assert r.status_code == 200
    data = r.json()
    assert "content" in data
    assert len(data["content"]) > 0


def test_worked_example_card_not_found(we_client):
    r = we_client.post("/api/cards/nonexistent-id/worked-example")
    assert r.status_code == 404


def test_worked_example_archived_card(we_client, db_session):
    _, card = _seed_card(db_session, archived=True)
    r = we_client.post(f"/api/cards/{card.id}/worked-example")
    assert r.status_code == 404


def test_worked_example_calls_llm_hard_tier(we_client, db_session, mock_llm):
    _, card = _seed_card(db_session)
    we_client.post(f"/api/cards/{card.id}/worked-example")
    assert len(mock_llm.calls) == 1
    assert mock_llm.calls[0]["tier"] == "hard"


def test_worked_example_rag_called_with_card_front(we_client, db_session, mock_rag):
    _, card = _seed_card(db_session)
    we_client.post(f"/api/cards/{card.id}/worked-example")
    mock_rag.search.assert_called_once()
    call_args = mock_rag.search.call_args
    # First positional arg is the query — should be card.front
    assert card.front in call_args[0][0]
