"""Tests for the Socratic coaching system-prompt builder."""
from app.db.models.concepts import Concept
from app.services.coaching_prompt import SENTINEL, build_system_prompt


def _concept() -> Concept:
    return Concept(
        id="k1",
        course_id="c1",
        name="SVD",
        type="definition",
        summary="Singular Value Decomposition factors A = U Σ V^T.",
        target_bloom=4,
    )


def test_prompt_contains_core_socratic_rules():
    prompt = build_system_prompt(_concept(), [], mode="deep")
    assert "Socratic tutor" in prompt
    assert "$...$" in prompt  # LaTeX rule
    assert "SVD" in prompt  # concept name


def test_prompt_instructs_misconception_correction():
    prompt = build_system_prompt(_concept(), [], mode="deep")
    # Must explicitly allow correcting a wrong answer with the precise definition.
    assert "misconception" in prompt.lower()
    assert "definition" in prompt.lower()


def test_prompt_explains_ready_sentinel():
    prompt = build_system_prompt(_concept(), [], mode="deep")
    assert SENTINEL in prompt
    assert SENTINEL == "[[READY]]"


def test_deep_and_review_modes_differ():
    deep = build_system_prompt(_concept(), [], mode="deep")
    review = build_system_prompt(_concept(), [], mode="review")
    assert deep != review
    # deep mode emphasises depth, review mode emphasises brevity
    assert "deep" in deep.lower()
    assert "brief" in review.lower() or "short" in review.lower()
