"""Coaching-API tests (unit, mocked LLM + RAG)."""
import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.api.coaching import (
    append_turn,
    count_turns,
    get_llm_gateway,
    get_rag,
    parse_transcript,
)
from app.db.models.concepts import Concept
from app.db.models.courses import Course
from app.db.models.coaching import CoachingSession
from app.main import app
from app.services.llm_gateway import StreamDelta, StreamDone, UsageInfo, Message


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _seed_course_and_concept(db_session, course_id: str = "c1", concept_id: str = "k1"):
    course = Course(id=course_id, name="Test Course")
    concept = Concept(
        id=concept_id,
        course_id=course_id,
        name="SVD",
        type="definition",
        summary="Singular Value Decomposition factors A = U Σ V^T.",
        target_bloom=4,
    )
    db_session.add_all([course, concept])
    db_session.commit()
    return course, concept


def _make_stream_events(text: str, tokens_in: int = 100, tokens_out: int = 50, cache_read: int = 0):
    """Yield delta events for each char-batch + a done event."""
    # Chunk into 5-char pieces to simulate streaming
    chunk = 5
    for i in range(0, len(text), chunk):
        yield StreamDelta(type="delta", text=text[i : i + chunk])
    yield StreamDone(
        type="done",
        usage=UsageInfo(
            input_tokens=tokens_in,
            output_tokens=tokens_out,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=cache_read,
        ),
        stop_reason="end_turn",
        model="test-model",
    )


@pytest.fixture
def mock_llm():
    """Mock LLMGateway that records calls and returns scripted streams."""
    gateway = MagicMock()
    gateway.responses = []  # list of (text, tokens_in, tokens_out, cache_read)
    gateway.calls = []  # list of (system, messages)

    def complete_stream(system, messages, tier="default", cache_breakpoints=None, max_tokens=1024):
        gateway.calls.append({"system": system, "messages": list(messages)})
        if gateway.responses:
            text, ti, to, cr = gateway.responses.pop(0)
        else:
            text, ti, to, cr = "Was meinst du?", 100, 50, 0
        return _make_stream_events(text, ti, to, cr)

    gateway.complete_stream = complete_stream
    return gateway


@pytest.fixture
def mock_rag():
    rag = MagicMock()
    rag.search = MagicMock(return_value=[])  # default: no context
    return rag


@pytest.fixture
def coaching_client(client, mock_llm, mock_rag):
    """Override LLM + RAG dependencies on the shared TestClient."""
    app.dependency_overrides[get_llm_gateway] = lambda: mock_llm
    app.dependency_overrides[get_rag] = lambda: mock_rag
    yield client
    # cleanup happens in conftest's client fixture


# ── Pure helpers ──────────────────────────────────────────────────────────────


def test_append_turn_first_block_no_leading_newlines():
    out = append_turn("", "hi", "Was?")
    assert out == "[USER]: hi\n[ASSISTANT]: Was?"


def test_append_turn_subsequent_block_separator():
    base = "[USER]: hi\n[ASSISTANT]: Was?"
    out = append_turn(base, "ok", "Genau.")
    assert out == "[USER]: hi\n[ASSISTANT]: Was?\n\n[USER]: ok\n[ASSISTANT]: Genau."


def test_parse_transcript_empty():
    assert parse_transcript(None) == []
    assert parse_transcript("") == []


def test_parse_transcript_round_trip():
    transcript = append_turn("", "hi", "Frage 1?")
    transcript = append_turn(transcript, "antwort", "Frage 2?")
    msgs = parse_transcript(transcript)
    assert [m.role for m in msgs] == ["user", "assistant", "user", "assistant"]
    assert [m.content for m in msgs] == ["hi", "Frage 1?", "antwort", "Frage 2?"]


def test_parse_transcript_handles_empty_user_opening():
    transcript = append_turn("", "", "Was unterscheidet SVD von EVD?")
    msgs = parse_transcript(transcript)
    assert len(msgs) == 2
    assert msgs[0].role == "user" and msgs[0].content == ""
    assert msgs[1].role == "assistant"


def test_count_turns():
    assert count_turns(None) == 0
    t = append_turn("", "", "A1")
    assert count_turns(t) == 1
    t = append_turn(t, "u1", "A2")
    assert count_turns(t) == 2


# ── Endpoint: create session ──────────────────────────────────────────────────


def test_create_session_returns_201_and_persists(coaching_client, db_session):
    _seed_course_and_concept(db_session)
    r = coaching_client.post(
        "/api/coaching/sessions",
        json={"course_id": "c1", "concept_id": "k1"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert "session_id" in body
    assert "started_at" in body

    # DB row exists
    row = db_session.get(CoachingSession, body["session_id"])
    assert row is not None
    assert row.course_id == "c1"
    assert row.concept_id == "k1"
    assert row.transcript == ""
    assert row.duration_min is None


def test_create_session_404_on_missing_course(coaching_client, db_session):
    _seed_course_and_concept(db_session)
    r = coaching_client.post(
        "/api/coaching/sessions",
        json={"course_id": "nope", "concept_id": "k1"},
    )
    assert r.status_code == 404


def test_create_session_404_on_missing_concept(coaching_client, db_session):
    _seed_course_and_concept(db_session)
    r = coaching_client.post(
        "/api/coaching/sessions",
        json={"course_id": "c1", "concept_id": "nope"},
    )
    assert r.status_code == 404


def test_create_session_404_when_concept_belongs_to_other_course(coaching_client, db_session):
    _seed_course_and_concept(db_session, "c1", "k1")
    other = Course(id="c2", name="Other")
    db_session.add(other)
    db_session.commit()
    r = coaching_client.post(
        "/api/coaching/sessions",
        json={"course_id": "c2", "concept_id": "k1"},
    )
    assert r.status_code == 404


# ── Endpoint: turn (streaming) ────────────────────────────────────────────────


def _consume_sse(response) -> list[dict]:
    """Read SSE response body and parse data lines as JSON."""
    events = []
    for line in response.iter_lines():
        if isinstance(line, bytes):
            line = line.decode()
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


def test_turn_streams_deltas_and_done(coaching_client, db_session, mock_llm):
    _seed_course_and_concept(db_session)
    session_id = coaching_client.post(
        "/api/coaching/sessions", json={"course_id": "c1", "concept_id": "k1"}
    ).json()["session_id"]

    mock_llm.responses.append(("Wie würdest du SVD definieren?", 200, 30, 0))

    with coaching_client.stream(
        "POST",
        f"/api/coaching/sessions/{session_id}/turn",
        json={"user_message": ""},
    ) as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]
        events = _consume_sse(r)

    deltas = [e for e in events if e["type"] == "delta"]
    dones = [e for e in events if e["type"] == "done"]
    assert len(deltas) > 0
    assert len(dones) == 1
    assert "".join(d["text"] for d in deltas) == "Wie würdest du SVD definieren?"
    assert dones[0]["tokens_in"] == 200
    assert dones[0]["tokens_out"] == 30


def test_turn_persists_transcript_after_done(coaching_client, db_session, mock_llm):
    _seed_course_and_concept(db_session)
    session_id = coaching_client.post(
        "/api/coaching/sessions", json={"course_id": "c1", "concept_id": "k1"}
    ).json()["session_id"]

    mock_llm.responses.append(("Frage 1?", 100, 20, 0))

    with coaching_client.stream(
        "POST",
        f"/api/coaching/sessions/{session_id}/turn",
        json={"user_message": ""},
    ) as r:
        _consume_sse(r)

    db_session.expire_all()
    row = db_session.get(CoachingSession, session_id)
    assert row is not None
    assert "[USER]: " in row.transcript
    assert "[ASSISTANT]: Frage 1?" in row.transcript


def test_turn_uses_history_in_messages(coaching_client, db_session, mock_llm):
    _seed_course_and_concept(db_session)
    session_id = coaching_client.post(
        "/api/coaching/sessions", json={"course_id": "c1", "concept_id": "k1"}
    ).json()["session_id"]

    # Turn 1 (opening)
    mock_llm.responses.append(("Frage 1?", 100, 20, 0))
    with coaching_client.stream(
        "POST", f"/api/coaching/sessions/{session_id}/turn", json={"user_message": ""}
    ) as r:
        _consume_sse(r)

    # Turn 2
    mock_llm.responses.append(("Frage 2?", 200, 25, 50))
    with coaching_client.stream(
        "POST",
        f"/api/coaching/sessions/{session_id}/turn",
        json={"user_message": "Meine Antwort"},
    ) as r:
        _consume_sse(r)

    # Turn 2 call should have history: [user(opening), assistant(Frage 1?), user("Meine Antwort")]
    second_call = mock_llm.calls[1]
    msgs = second_call["messages"]
    assert len(msgs) == 3
    assert msgs[0].role == "user"
    assert msgs[1].role == "assistant" and msgs[1].content == "Frage 1?"
    assert msgs[2].role == "user" and msgs[2].content == "Meine Antwort"


def test_turn_404_on_unknown_session(coaching_client):
    r = coaching_client.post(
        f"/api/coaching/sessions/{uuid.uuid4()}/turn", json={"user_message": "x"}
    )
    assert r.status_code == 404


def test_turn_409_on_ended_session(coaching_client, db_session):
    _seed_course_and_concept(db_session)
    session_id = coaching_client.post(
        "/api/coaching/sessions", json={"course_id": "c1", "concept_id": "k1"}
    ).json()["session_id"]
    coaching_client.post(f"/api/coaching/sessions/{session_id}/end")

    r = coaching_client.post(
        f"/api/coaching/sessions/{session_id}/turn", json={"user_message": "x"}
    )
    assert r.status_code == 409


def test_turn_includes_socratic_rules_in_system_prompt(coaching_client, db_session, mock_llm):
    _seed_course_and_concept(db_session)
    session_id = coaching_client.post(
        "/api/coaching/sessions", json={"course_id": "c1", "concept_id": "k1"}
    ).json()["session_id"]

    mock_llm.responses.append(("Q?", 50, 10, 0))
    with coaching_client.stream(
        "POST", f"/api/coaching/sessions/{session_id}/turn", json={"user_message": ""}
    ) as r:
        _consume_sse(r)

    sys_prompt = mock_llm.calls[0]["system"]
    assert "NEVER give a direct answer" in sys_prompt
    assert "SVD" in sys_prompt  # concept name
    assert "$...$" in sys_prompt  # LaTeX rule


def test_turn_invokes_rag_with_concept_query(coaching_client, db_session, mock_llm, mock_rag):
    _seed_course_and_concept(db_session)
    session_id = coaching_client.post(
        "/api/coaching/sessions", json={"course_id": "c1", "concept_id": "k1"}
    ).json()["session_id"]

    mock_llm.responses.append(("Q?", 50, 10, 0))
    with coaching_client.stream(
        "POST", f"/api/coaching/sessions/{session_id}/turn", json={"user_message": ""}
    ) as r:
        _consume_sse(r)

    mock_rag.search.assert_called_once()
    call = mock_rag.search.call_args
    assert call.args[0] == "c1"  # course_id
    assert "SVD" in call.args[1]  # query contains concept name
    assert call.kwargs.get("k") == 5 or (len(call.args) >= 3 and call.args[2] == 5)


# ── Endpoint: end session ─────────────────────────────────────────────────────


def test_end_session_sets_duration_and_returns_turn_count(coaching_client, db_session, mock_llm):
    _seed_course_and_concept(db_session)
    session_id = coaching_client.post(
        "/api/coaching/sessions", json={"course_id": "c1", "concept_id": "k1"}
    ).json()["session_id"]

    # Mock some historical started_at
    row = db_session.get(CoachingSession, session_id)
    row.started_at = datetime.now(timezone.utc) - timedelta(minutes=12, seconds=30)
    db_session.commit()

    # 2 turns
    for _ in range(2):
        mock_llm.responses.append(("Q?", 50, 10, 0))
        with coaching_client.stream(
            "POST", f"/api/coaching/sessions/{session_id}/turn", json={"user_message": "x"}
        ) as r:
            _consume_sse(r)

    r = coaching_client.post(f"/api/coaching/sessions/{session_id}/end")
    assert r.status_code == 200
    body = r.json()
    assert body["session_id"] == session_id
    assert body["turn_count"] == 2
    assert 12.0 <= body["duration_min"] <= 13.0


def test_end_session_404_unknown(coaching_client):
    r = coaching_client.post(f"/api/coaching/sessions/{uuid.uuid4()}/end")
    assert r.status_code == 404


# ── Endpoint: GET session ─────────────────────────────────────────────────────


def test_get_session_returns_full_data(coaching_client, db_session, mock_llm):
    _seed_course_and_concept(db_session)
    session_id = coaching_client.post(
        "/api/coaching/sessions", json={"course_id": "c1", "concept_id": "k1"}
    ).json()["session_id"]

    mock_llm.responses.append(("Frage?", 50, 10, 0))
    with coaching_client.stream(
        "POST", f"/api/coaching/sessions/{session_id}/turn", json={"user_message": ""}
    ) as r:
        _consume_sse(r)

    r = coaching_client.get(f"/api/coaching/sessions/{session_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == session_id
    assert body["concept_id"] == "k1"
    assert "[ASSISTANT]: Frage?" in body["transcript"]


def test_get_session_404(coaching_client):
    r = coaching_client.get(f"/api/coaching/sessions/{uuid.uuid4()}")
    assert r.status_code == 404


# ── Endpoint: list sessions ───────────────────────────────────────────────────


def test_list_sessions_for_course(coaching_client, db_session):
    _seed_course_and_concept(db_session)
    s1 = coaching_client.post(
        "/api/coaching/sessions", json={"course_id": "c1", "concept_id": "k1"}
    ).json()["session_id"]
    s2 = coaching_client.post(
        "/api/coaching/sessions", json={"course_id": "c1", "concept_id": "k1"}
    ).json()["session_id"]

    r = coaching_client.get("/api/courses/c1/coaching/sessions")
    assert r.status_code == 200
    items = r.json()
    ids = [s["id"] for s in items]
    assert s1 in ids and s2 in ids


def test_list_sessions_empty_course(coaching_client, db_session):
    _seed_course_and_concept(db_session)
    r = coaching_client.get("/api/courses/no-such-course/coaching/sessions")
    assert r.status_code == 200
    assert r.json() == []
