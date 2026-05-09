"""LLM-based card generation for Knowledge Graph Refinement."""
import json
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.cards import Card
from app.db.models.concepts import Concept
from app.db.models.reviews import Review
from app.services.llm_gateway import LLMGateway, Message
from app.services.rag import RAGService

logger = logging.getLogger(__name__)

AGAIN_THRESHOLD = 3
LOOKBACK_DAYS = 14

_SYSTEM_TEMPLATE = """\
Du bist ein Didaktik-Experte für ML-Mathematik an der Universität Tübingen.

Konzept: {concept_name}
Beschreibung: {concept_summary}

{rag_section}

Bestehende Karten (werden NICHT automatisch gelöscht):
{existing_cards}

Generiere 3–5 neue Lernkarten-Vorschläge, die ANDERE Perspektiven beleuchten:
- Geometrische oder intuitive Sichtweise
- Anwendungsbeispiel
- Kontra-Beispiel / Abgrenzung
- Verbindung zu anderen Konzepten

Antworte ausschließlich als JSON-Array (kein Prosa, kein Markdown-Wrapper):
[{{"question": "...", "answer": "...", "rationale": "..."}}]
"""

_NO_RAG = "(Kein Kursmaterial indexiert — Generierung aus allgemeinem Wissen)"


def compute_again_count(db: Session, concept_id: str) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=LOOKBACK_DAYS)
    count = db.scalar(
        select(func.count())
        .select_from(Review)
        .join(Card, Review.card_id == Card.id)
        .where(
            Card.concept_id == concept_id,
            Review.rating == 1,
            Review.reviewed_at >= cutoff,
        )
    )
    return count or 0


def _build_rag_section(hits: list[Any]) -> str:
    if not hits:
        return _NO_RAG
    lines = ["Kontext aus dem Kursmaterial:"]
    for i, hit in enumerate(hits, 1):
        page = f"S.{hit.page}" if hit.page is not None else "Seite unbekannt"
        lines.append(f"\n### Auszug {i} ({page})\n{hit.content}")
    return "\n".join(lines)


def _build_existing_cards_summary(cards: list[Card]) -> str:
    if not cards:
        return "(Keine bestehenden Karten)"
    lines = []
    for i, c in enumerate(cards, 1):
        lines.append(f"{i}. F: {c.front or '?'}\n   A: {c.back or '?'}")
    return "\n".join(lines)


def _parse_proposed_cards(text: str) -> list[dict[str, Any]]:
    stripped = text.strip()
    try:
        result: list[dict[str, Any]] = json.loads(stripped)
        return result
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", stripped)
    if match:
        try:
            result = json.loads(match.group(1).strip())
            return result
        except json.JSONDecodeError:
            pass
    raise ValueError("LLM returned invalid JSON")


def generate_proposed_cards(
    llm: LLMGateway,
    rag: RAGService,
    concept: Concept,
    existing_cards: list[Card],
) -> list[dict[str, Any]]:
    hits = rag.search(concept.name or "", concept.course_id or "", k=5)
    system_prompt = _SYSTEM_TEMPLATE.format(
        concept_name=concept.name or "",
        concept_summary=concept.summary or "(keine Beschreibung)",
        rag_section=_build_rag_section(hits),
        existing_cards=_build_existing_cards_summary(existing_cards),
    )
    response = llm.complete(
        system_prompt,
        [Message(role="user", content=f"Generiere neue Karten-Vorschläge für das Konzept: {concept.name or ''}.")],
        tier="default",
        max_tokens=1024,
    )
    raw = _parse_proposed_cards(response.text)
    proposed: list[dict[str, Any]] = []
    for i, item in enumerate(raw):
        proposed.append(
            {
                "index": i,
                "question": item.get("question", ""),
                "answer": item.get("answer", ""),
                "rationale": item.get("rationale", ""),
                "card_status": "pending",
            }
        )
    return proposed
