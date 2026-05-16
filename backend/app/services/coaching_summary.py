"""End-of-coaching conclusion: a recap summary + a small multiple-choice quiz.

Generated once when a coaching session ends — a single LLM call (default tier)
that produces both, sharing the transcript context. See
specs/phase3_coaching_refinement.md.
"""
import json
import logging
from typing import Any

from app.db.models.concepts import Concept
from app.services.coaching_prompt import build_rag_context
from app.services.llm_gateway import LLMGateway, Message
from app.services.rag import ChunkHit

logger = logging.getLogger(__name__)


CONCLUSION_SYSTEM = """
You conclude a Socratic coaching session for a graduate Machine Learning student
(M.Sc. ML, Universität Tübingen). You receive the concept, the full dialogue
transcript, and the course source material.

Produce TWO things:

1. SUMMARY — a short pedagogical recap that locks in the learning:
   - the ONE core idea of the concept
   - the precise, correct definition
   - what was covered, and any point the student struggled with
   Markdown, LaTeX for math (inline $...$, display $$...$$). 4–8 sentences. German.

2. QUIZ — 2 to 4 multiple-choice questions checking understanding of the CORE.
   Short and core-focused, no trivia. Each question has 3–4 options, exactly one
   correct. German. LaTeX for math.

# OUTPUT CONTRACT
Respond with exactly ONE JSON object, nothing else — no prose, no markdown fences:
{
  "summary": string,
  "quiz": [
    {
      "question": string,
      "options": [string, string, string],
      "correct_index": integer,
      "explanation": string
    }
  ]
}
""".strip()


def generate_conclusion(
    concept: Concept,
    transcript: str | None,
    hits: list[ChunkHit],
    gateway: LLMGateway,
) -> tuple[str | None, list[dict[str, Any]]]:
    """Generate the summary + quiz for a finished coaching session.

    Returns ``(summary, quiz)``. Returns ``(None, [])`` for an empty transcript
    (no call made) or on any LLM / parsing failure — the caller treats a missing
    conclusion as non-fatal.
    """
    if not transcript or not transcript.strip():
        return None, []

    user_msg = (
        f"## Concept\n"
        f"- Name: {concept.name}\n"
        f"- Type: {concept.type or 'N/A'}\n"
        f"- Summary: {concept.summary or 'N/A'}\n\n"
        f"## Dialogue transcript\n{transcript}\n\n"
        f"{build_rag_context(hits)}\n\n"
        f"Write the summary and quiz as the specified JSON object."
    )

    try:
        response = gateway.complete(
            system=CONCLUSION_SYSTEM,
            messages=[Message(role="user", content=user_msg)],
            tier="default",
            max_tokens=1500,
        )
        summary, quiz = _parse_conclusion(response.text)
    except Exception:
        logger.exception("coaching_conclusion_failed", extra={"concept_id": concept.id})
        return None, []

    logger.info(
        "coaching_conclusion_generated",
        extra={"concept_id": concept.id, "quiz_count": len(quiz)},
    )
    return summary, quiz


def _parse_conclusion(raw: str) -> tuple[str | None, list[dict[str, Any]]]:
    """Parse the LLM JSON object into ``(summary, quiz)``.

    Raises ValueError on unparseable output. Individual malformed quiz items are
    dropped rather than failing the whole conclusion.
    """
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip().rstrip("`").strip()

    try:
        data: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"conclusion JSON parse error: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("conclusion response is not a JSON object")

    summary_raw = str(data.get("summary", "")).strip()
    summary = summary_raw or None

    quiz: list[dict[str, Any]] = []
    for item in data.get("quiz", []) if isinstance(data.get("quiz"), list) else []:
        question = _valid_quiz_item(item)
        if question is not None:
            quiz.append(question)

    return summary, quiz


def _valid_quiz_item(item: Any) -> dict[str, Any] | None:
    """Return a normalised quiz item, or None if it is malformed."""
    if not isinstance(item, dict):
        return None
    question = str(item.get("question", "")).strip()
    raw_options = item.get("options")
    if not question or not isinstance(raw_options, list):
        return None
    options = [str(o).strip() for o in raw_options if str(o).strip()]
    if len(options) < 2:
        return None
    try:
        correct_index = int(item.get("correct_index"))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not 0 <= correct_index < len(options):
        return None
    explanation = str(item.get("explanation", "")).strip()
    return {
        "question": question,
        "options": options,
        "correct_index": correct_index,
        "explanation": explanation,
    }
