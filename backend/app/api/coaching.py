import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Iterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.schemas.coaching import (
    CoachingSessionCreate,
    CoachingSessionCreated,
    CoachingSessionEnded,
    CoachingSessionListItem,
    CoachingSessionResponse,
    CoachingTurnRequest,
)
from app.db.models.coaching import CoachingSession
from app.db.models.concepts import Concept
from app.db.models.courses import Course
from app.db.session import get_db
from app.services.coaching_prompt import SENTINEL, Mode, build_system_prompt
from app.services.coaching_summary import generate_conclusion
from app.services.llm_gateway import LLMGateway, Message, StreamDelta, StreamDone
from app.services.rag import RAGService, get_rag_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["coaching"])

# Module-level singletons (injected via Depends so tests can override)
_llm_gateway: LLMGateway | None = None


def get_llm_gateway() -> LLMGateway:
    global _llm_gateway
    if _llm_gateway is None:
        _llm_gateway = LLMGateway()
    return _llm_gateway


def get_rag() -> RAGService:
    return get_rag_service()


# ── Transcript helpers ────────────────────────────────────────────────────────

_TURN_SPLIT = re.compile(r"\n?\[(USER|ASSISTANT)\]: ", re.MULTILINE)


def parse_transcript(transcript: str | None) -> list[Message]:
    """Parse the stored transcript text back into a Message list.

    Format produced by `append_turn`:
        [USER]: <user_message>
        [ASSISTANT]: <assistant_message>

        [USER]: ...
        [ASSISTANT]: ...
    """
    if not transcript:
        return []

    parts = _TURN_SPLIT.split(transcript)
    # parts[0] is leading text before first marker (usually "" or junk)
    messages: list[Message] = []
    i = 1
    while i + 1 < len(parts):
        role = "user" if parts[i] == "USER" else "assistant"
        content = parts[i + 1].rstrip()
        # strip trailing blank lines that came from the \n\n separator
        content = content.rstrip("\n").rstrip()
        messages.append(Message(role=role, content=content))  # type: ignore[arg-type]
        i += 2
    return messages


def append_turn(transcript: str | None, user_message: str, assistant_message: str) -> str:
    block = f"[USER]: {user_message}\n[ASSISTANT]: {assistant_message}"
    if not transcript:
        return block
    return f"{transcript}\n\n{block}"


def count_turns(transcript: str | None) -> int:
    if not transcript:
        return 0
    return transcript.count("[ASSISTANT]:")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/api/coaching/sessions",
    status_code=201,
    response_model=CoachingSessionCreated,
)
def create_session(
    body: CoachingSessionCreate,
    db: Session = Depends(get_db),
) -> CoachingSessionCreated:
    course = db.get(Course, body.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    concept = db.get(Concept, body.concept_id)
    if not concept or concept.course_id != body.course_id:
        raise HTTPException(status_code=404, detail="Concept not found in course")

    now = datetime.now(timezone.utc)
    session = CoachingSession(
        id=str(uuid.uuid4()),
        course_id=body.course_id,
        concept_id=body.concept_id,
        transcript="",
        diagnostic=None,
        duration_min=None,
        started_at=now,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    logger.info(
        "coaching_session_created",
        extra={"session_id": session.id, "course_id": body.course_id, "concept_id": body.concept_id},
    )
    return CoachingSessionCreated(session_id=session.id, started_at=now)


@router.post("/api/coaching/sessions/{session_id}/turn")
def turn(
    session_id: str,
    body: CoachingTurnRequest,
    db: Session = Depends(get_db),
    llm: LLMGateway = Depends(get_llm_gateway),
    rag: RAGService = Depends(get_rag),
) -> StreamingResponse:
    session = db.get(CoachingSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.duration_min is not None:
        raise HTTPException(status_code=409, detail="Session already ended")

    concept = db.get(Concept, session.concept_id) if session.concept_id else None
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found for session")

    # Build system prompt with RAG context
    rag_query = " ".join(filter(None, [concept.name, concept.summary]))
    hits = rag.search(session.course_id or "", rag_query, k=5) if session.course_id else []
    mode: Mode = "deep" if concept.stage in ("new", "explained") else "review"
    system_prompt = build_system_prompt(concept, hits, mode)

    # Build messages list from transcript history + new user_message
    history = parse_transcript(session.transcript)
    user_text = body.user_message.strip()

    messages = list(history)
    # The LLM API requires non-empty user content. For the opening turn (empty user_message,
    # empty history), substitute a neutral starter trigger.
    if not user_text and not history:
        api_user = "(Beginne das Coaching mit einer offenen Diagnose-Frage zum Konzept.)"
    elif not user_text:
        # Empty input mid-session — treat as "I don't know, please continue" so the LLM gets context.
        api_user = "(Der Studierende stockt — bitte stelle eine kleinere Sub-Frage.)"
    else:
        api_user = user_text
    messages.append(Message(role="user", content=api_user))

    turn_index = count_turns(session.transcript)
    start = time.monotonic()

    def event_generator() -> Iterator[bytes]:
        full_response = ""
        flushed = 0  # chars of `full_response` already streamed to the client
        usage_info = {"tokens_in": 0, "tokens_out": 0, "cache_read": 0}
        try:
            for event in llm.complete_stream(
                system=system_prompt,
                messages=messages,
                tier="default",
                max_tokens=1024,
            ):
                if isinstance(event, StreamDelta):
                    full_response += event.text
                    # Withhold a trailing window that could be a [[READY]] sentinel,
                    # so the machine signal never reaches the user's screen.
                    safe = len(full_response.rstrip()) - len(SENTINEL)
                    if safe > flushed:
                        chunk = full_response[flushed:safe]
                        flushed = safe
                        yield f'data: {json.dumps({"type": "delta", "text": chunk})}\n\n'.encode()
                elif isinstance(event, StreamDone):
                    usage_info = {
                        "tokens_in": event.usage.input_tokens,
                        "tokens_out": event.usage.output_tokens,
                        "cache_read": event.usage.cache_read_input_tokens,
                    }
        except Exception as exc:
            logger.exception("coaching_turn_stream_failed", extra={"session_id": session_id})
            yield f'data: {json.dumps({"type": "error", "message": str(exc)})}\n\n'.encode()
            return

        # Resolve the sentinel: if the coach signalled readiness, strip it from
        # the visible/persisted text and surface it as a `ready` flag instead.
        stripped = full_response.rstrip()
        ready = stripped.endswith(SENTINEL)
        clean = stripped[: -len(SENTINEL)].rstrip() if ready else full_response

        # Flush any remaining (non-sentinel) text held back by the buffer.
        if len(clean) > flushed:
            yield f'data: {json.dumps({"type": "delta", "text": clean[flushed:]})}\n\n'.encode()

        # Persist updated transcript (use api_user, not raw user_text, since api_user has fallbacks for empty input)
        session.transcript = append_turn(session.transcript, api_user, clean)
        db.commit()

        latency_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "coaching_turn",
            extra={
                "session_id": session_id,
                "concept_id": session.concept_id,
                "turn_index": turn_index,
                "user_message_chars": len(user_text),
                "assistant_message_chars": len(clean),
                "ready": ready,
                "tokens_in": usage_info["tokens_in"],
                "tokens_out": usage_info["tokens_out"],
                "cache_read": usage_info["cache_read"],
                "latency_ms": latency_ms,
            },
        )

        yield f'data: {json.dumps({"type": "done", "ready": ready, **usage_info})}\n\n'.encode()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post(
    "/api/coaching/sessions/{session_id}/end",
    response_model=CoachingSessionEnded,
)
def end_session(
    session_id: str,
    db: Session = Depends(get_db),
    llm: LLMGateway = Depends(get_llm_gateway),
    rag: RAGService = Depends(get_rag),
) -> CoachingSessionEnded:
    session = db.get(CoachingSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    started = session.started_at
    if started and started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    duration_min = (
        (datetime.now(timezone.utc) - started).total_seconds() / 60.0 if started else 0.0
    )
    session.duration_min = duration_min

    # Advance the learn-mode lifecycle: a finished coaching session marks the
    # concept as 'coached'. Cards are generated separately (not here).
    concept = db.get(Concept, session.concept_id) if session.concept_id else None
    if concept and concept.stage in ("new", "explained"):
        concept.stage = "coached"

    # Generate the end-of-session conclusion (recap summary + mini-quiz). Best
    # effort: a generation failure must not block the session from ending, and
    # the stage transition above stands regardless.
    summary: str | None = None
    quiz: list[dict[str, Any]] = []
    if concept and session.transcript:
        rag_query = " ".join(filter(None, [concept.name, concept.summary]))
        hits = rag.search(session.course_id or "", rag_query, k=5) if session.course_id else []
        summary, quiz = generate_conclusion(concept, session.transcript, hits, llm)
        session.summary = summary
        session.quiz = quiz

    db.commit()

    return CoachingSessionEnded(
        session_id=session.id,
        duration_min=duration_min,
        turn_count=count_turns(session.transcript),
        summary=summary,
        quiz=quiz,  # type: ignore[arg-type]
    )


@router.get(
    "/api/coaching/sessions/{session_id}",
    response_model=CoachingSessionResponse,
)
def get_session(session_id: str, db: Session = Depends(get_db)) -> CoachingSessionResponse:
    session = db.get(CoachingSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return CoachingSessionResponse.model_validate(session)


@router.get(
    "/api/courses/{course_id}/coaching/sessions",
    response_model=list[CoachingSessionListItem],
)
def list_sessions(
    course_id: str,
    db: Session = Depends(get_db),
) -> list[CoachingSessionListItem]:
    rows = (
        db.query(CoachingSession)
        .filter(CoachingSession.course_id == course_id)
        .order_by(CoachingSession.started_at.desc())
        .all()
    )
    return [CoachingSessionListItem.model_validate(r) for r in rows]
