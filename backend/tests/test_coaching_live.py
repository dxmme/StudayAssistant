"""Live coaching test — hits real Anthropic API. Marked @live so default suite skips it.

Verifies prompt-caching kicks in on turn 2 (cache_read_input_tokens > 0).
"""
import json
from unittest.mock import MagicMock

import pytest

from app.api.coaching import get_llm_gateway, get_rag
from app.db.models.concepts import Concept
from app.db.models.courses import Course
from app.main import app
from app.services.llm_gateway import LLMGateway


def _consume_sse(response) -> tuple[str, dict]:
    """Read SSE response, return (full_text, done_event)."""
    text = ""
    done = {}
    for line in response.iter_lines():
        if isinstance(line, bytes):
            line = line.decode()
        if line.startswith("data: "):
            event = json.loads(line[6:])
            if event["type"] == "delta":
                text += event["text"]
            elif event["type"] == "done":
                done = event
    return text, done


@pytest.mark.live
def test_coaching_session_two_turns_cache_read_works(client, db_session):
    """Turn 1 creates cache, Turn 2 should read from it."""
    # Seed concept + course
    course = Course(id="live-c", name="Live Course")
    # Long summary so the system prompt crosses the 1024-token cache threshold
    long_summary = "Singular Value Decomposition factors a real matrix A as " * 200
    concept = Concept(
        id="live-k",
        course_id="live-c",
        name="SVD",
        type="definition",
        summary=long_summary,
        target_bloom=4,
    )
    db_session.add_all([course, concept])
    db_session.commit()

    # Use real LLM, mock RAG (no Chroma in test env)
    mock_rag = MagicMock()
    mock_rag.search = MagicMock(return_value=[])
    app.dependency_overrides[get_rag] = lambda: mock_rag
    app.dependency_overrides[get_llm_gateway] = lambda: LLMGateway()

    session_id = client.post(
        "/api/coaching/sessions",
        json={"course_id": "live-c", "concept_id": "live-k"},
    ).json()["session_id"]

    # Turn 1 (opening) — creates cache
    with client.stream(
        "POST",
        f"/api/coaching/sessions/{session_id}/turn",
        json={"user_message": ""},
    ) as r:
        text1, done1 = _consume_sse(r)

    assert text1, "Expected non-empty assistant response in turn 1"
    assert done1.get("tokens_in", 0) > 1000, f"system prompt should be >1k tokens; got {done1}"

    # Turn 2 — should read cache
    with client.stream(
        "POST",
        f"/api/coaching/sessions/{session_id}/turn",
        json={"user_message": "Eigenwertzerlegung gilt nur für quadratische Matrizen."},
    ) as r:
        text2, done2 = _consume_sse(r)

    assert text2
    assert done2.get("cache_read", 0) > 0, (
        f"Expected cache_read > 0 on turn 2, got {done2}"
    )
