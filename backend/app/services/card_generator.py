import json
import logging
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models.cards import Card
from app.db.models.concepts import Concept
from app.services.llm_gateway import LLMGateway
from app.services.rag import RAGService

logger = logging.getLogger(__name__)


def generate_card_for_concept(
    concept: Concept,
    db: Session,
    rag: RAGService,
) -> Card:
    """
    Generate a single flashcard (front/back) for a concept using LLM + RAG context.

    Returns the created Card model (not yet committed).
    """
    gateway = LLMGateway()

    # Get RAG context (top 3 chunks related to this concept)
    rag_hits = rag.search(
        course_id=concept.course_id or "",
        query=concept.name,
        k=3,
    )
    context_text = "\n\n".join([hit.content for hit in rag_hits])

    # Build prompt
    system_prompt = (
        "You are an expert educator. Generate a single flashcard question-answer pair "
        "for the given concept. The answer should be detailed but concise (2-3 sentences). "
        "Format as JSON: {\"front\": \"...\", \"back\": \"...\"}"
    )

    user_message = (
        f"Concept: {concept.name}\n"
        f"Type: {concept.type}\n"
        f"Summary: {concept.summary or 'N/A'}\n\n"
        f"Context from materials:\n{context_text}\n\n"
        f"Generate a flashcard in JSON format with 'front' (question) and 'back' (answer) fields."
    )

    try:
        response = gateway.complete(
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            tier="default",
        )

        # Parse LLM response as JSON
        card_data = json.loads(response)
        front = card_data.get("front", "")
        back = card_data.get("back", "")
    except Exception as exc:
        logger.warning(
            "card_generation_failed",
            extra={"concept_id": concept.id, "error": str(exc)},
        )
        # Fallback: use concept name as question
        front = f"Define: {concept.name}"
        back = concept.summary or f"[LLM failed to generate answer for {concept.name}]"

    # Initialize FSRS state (new card, not yet reviewed)
    fsrs_state = {
        "stability": 0,
        "difficulty": 0,
        "due": datetime.now().isoformat(),
        "review_count": 0,
        "lapse_count": 0,
    }

    card = Card(
        id=str(uuid.uuid4()),
        course_id=concept.course_id,
        concept_id=concept.id,
        type="concept-qa",
        front=front,
        back=back,
        bloom_level=concept.target_bloom,
        fsrs_state=fsrs_state,
        created_at=datetime.now(),
        archived=False,
    )

    return card
