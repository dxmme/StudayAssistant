import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas.worked_examples import WorkedExampleResponse
from app.db.models.cards import Card
from app.db.session import get_db
from app.services.llm_gateway import LLMGateway, Message
from app.services.rag import RAGService, get_rag_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["worked-examples"])

_llm_gateway: LLMGateway | None = None


def get_llm_gateway() -> LLMGateway:
    global _llm_gateway
    if _llm_gateway is None:
        _llm_gateway = LLMGateway()
    return _llm_gateway


def get_rag() -> RAGService:
    return get_rag_service()


_SYSTEM_TEMPLATE = """\
Du bist ein Lernassistent für ML-Master-Studenten an der Universität Tübingen.
Erstelle ein vollständiges Worked Example für die folgende Aufgabe.

{rag_section}

Format (Markdown + LaTeX für mathematische Ausdrücke):

## Worked Example

**Problem:** [Aufgabe nochmal klar formuliert]

**Lösung:**
[Schritt-für-Schritt, jeder Schritt nummeriert, mathematische Ausdrücke in LaTeX]

**Key Insight:** [1–2 Sätze — warum funktioniert das so?]
"""

_NO_RAG = "(Kein Kursmaterial indexiert — Lösung aus allgemeinem Wissen)"


def _build_rag_section(hits: list) -> str:
    if not hits:
        return _NO_RAG
    lines = ["Kontext aus dem Kursmaterial:"]
    for i, hit in enumerate(hits, 1):
        page = f"S.{hit.page}" if hit.page is not None else "Seite unbekannt"
        lines.append(f"\n### Auszug {i} ({page})\n{hit.content}")
    return "\n".join(lines)


@router.post("/cards/{card_id}/worked-example", response_model=WorkedExampleResponse)
def generate_worked_example(
    card_id: str,
    db: Session = Depends(get_db),
    llm: LLMGateway = Depends(get_llm_gateway),
    rag: RAGService = Depends(get_rag),
) -> WorkedExampleResponse:
    card = db.get(Card, card_id)
    if card is None or card.archived:
        raise HTTPException(status_code=404, detail="Card not found")

    hits = rag.search(card.front or "", card.course_id or "", k=3)
    system_prompt = _SYSTEM_TEMPLATE.format(rag_section=_build_rag_section(hits))

    user_msg = f"Aufgabe: {card.front or ''}\n\nAntwort laut Karte: {card.back or ''}"
    response = llm.complete(
        system_prompt,
        [Message(role="user", content=user_msg)],
        tier="hard",
        max_tokens=1024,
    )
    return WorkedExampleResponse(content=response.text)
