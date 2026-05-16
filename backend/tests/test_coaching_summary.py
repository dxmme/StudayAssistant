"""Tests for the end-of-coaching conclusion service (summary + quiz)."""
import json
from unittest.mock import MagicMock

from app.db.models.concepts import Concept
from app.services.coaching_summary import generate_conclusion
from app.services.llm_gateway import LLMResponse, UsageInfo


def _concept() -> Concept:
    return Concept(
        id="k1",
        course_id="c1",
        name="SVD",
        type="definition",
        summary="Singular Value Decomposition factors A = U Σ V^T.",
        target_bloom=4,
    )


def _gateway(text: str) -> MagicMock:
    gw = MagicMock()
    gw.complete = MagicMock(
        return_value=LLMResponse(
            text=text,
            model="test-model",
            usage=UsageInfo(0, 0, 0, 0),
            stop_reason="end_turn",
        )
    )
    return gw


_VALID = json.dumps(
    {
        "summary": "Die SVD zerlegt $A = U\\Sigma V^T$ ...",
        "quiz": [
            {
                "question": "Was sind die Spalten von $U$?",
                "options": ["Eigenvektoren von $A$", "Linkssinguläre Vektoren", "Zufällig"],
                "correct_index": 1,
                "explanation": "Die Spalten von U sind die linkssingulären Vektoren.",
            },
            {
                "question": "Was enthält $\\Sigma$?",
                "options": ["Singulärwerte", "Eigenwerte von $A$"],
                "correct_index": 0,
                "explanation": "Sigma trägt die Singulärwerte auf der Diagonale.",
            },
        ],
    }
)


def test_generate_conclusion_returns_summary_and_quiz():
    gw = _gateway(_VALID)
    summary, quiz = generate_conclusion(_concept(), "[USER]: hi\n[ASSISTANT]: Frage?", [], gw)
    assert summary is not None and "SVD" in summary
    assert 2 <= len(quiz) <= 4
    for q in quiz:
        assert q["question"]
        assert len(q["options"]) >= 2
        assert 0 <= q["correct_index"] < len(q["options"])
        assert "explanation" in q


def test_generate_conclusion_empty_transcript_skips_call():
    gw = _gateway(_VALID)
    summary, quiz = generate_conclusion(_concept(), "", [], gw)
    assert summary is None and quiz == []
    gw.complete.assert_not_called()


def test_generate_conclusion_none_transcript_skips_call():
    gw = _gateway(_VALID)
    summary, quiz = generate_conclusion(_concept(), None, [], gw)
    assert summary is None and quiz == []
    gw.complete.assert_not_called()


def test_generate_conclusion_llm_error_returns_empty():
    gw = MagicMock()
    gw.complete = MagicMock(side_effect=RuntimeError("boom"))
    summary, quiz = generate_conclusion(_concept(), "[USER]: x\n[ASSISTANT]: y", [], gw)
    assert summary is None and quiz == []


def test_generate_conclusion_malformed_json_returns_empty():
    gw = _gateway("not json at all {{{")
    summary, quiz = generate_conclusion(_concept(), "[USER]: x\n[ASSISTANT]: y", [], gw)
    assert summary is None and quiz == []


def test_generate_conclusion_drops_malformed_quiz_item_keeps_summary():
    raw = json.dumps(
        {
            "summary": "Recap text.",
            "quiz": [
                {"question": "good?", "options": ["a", "b"], "correct_index": 0, "explanation": "x"},
                {"question": "bad — index out of range", "options": ["a", "b"], "correct_index": 9, "explanation": "x"},
                {"question": "bad — one option", "options": ["only"], "correct_index": 0, "explanation": "x"},
            ],
        }
    )
    gw = _gateway(raw)
    summary, quiz = generate_conclusion(_concept(), "[USER]: x\n[ASSISTANT]: y", [], gw)
    assert summary == "Recap text."
    assert len(quiz) == 1
    assert quiz[0]["question"] == "good?"


def test_generate_conclusion_strips_code_fences():
    gw = _gateway(f"```json\n{_VALID}\n```")
    summary, quiz = generate_conclusion(_concept(), "[USER]: x\n[ASSISTANT]: y", [], gw)
    assert summary is not None
    assert len(quiz) == 2
