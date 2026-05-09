import logging
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.concepts import Concept
from app.db.models.materials import Material, MaterialChunk
from app.services import chunker as chunker_svc
from app.services import concept_extractor as extractor_svc
from app.services import embedder as embedder_svc
from app.services.llm_gateway import LLMGateway
from app.services.rag import RAGService

logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    chunks: int
    concepts: int
    duration_ms: int


class IngestError(Exception):
    def __init__(self, message: str, step: str) -> None:
        super().__init__(message)
        self.step = step


def run_ingest(material: Material, db: Session, rag: RAGService) -> IngestResult:
    """
    Full ingest pipeline for a single material.
    Rolls back DB rows and Chroma upserts on any failure.
    """
    if not material.file_path:
        raise IngestError("No file_path on material", step="load")

    md_path = Path(material.file_path).with_suffix(".md")
    if not md_path.exists():
        raise IngestError("Markdown sidecar missing — re-upload the material", step="load")

    t0 = time.monotonic()
    created_chunk_ids: list[str] = []
    created_concept_ids: list[str] = []

    try:
        # Step 1 — Load markdown
        markdown = md_path.read_text(encoding="utf-8")

        # Step 2 — Chunk
        chunks = chunker_svc.chunk_markdown(markdown)
        if not chunks:
            raise IngestError("Chunking produced zero chunks", step="chunk")

        # Step 3 — Embed (batch all chunks in one API call)
        contents = [c.content for c in chunks]
        embeddings = embedder_svc.embed_texts(contents)

        # Step 4 — Write material_chunks to DB
        chunk_ids = [str(uuid.uuid4()) for _ in chunks]
        for chunk_id, chunk, embedding in zip(chunk_ids, chunks, embeddings):
            db_chunk = MaterialChunk(
                id=chunk_id,
                material_id=material.id,
                course_id=material.course_id,
                content=chunk.content,
                page=chunk.page,
                chunk_index=chunk.chunk_index,
                token_count=chunk.token_count,
            )
            db.add(db_chunk)
            created_chunk_ids.append(chunk_id)
        db.flush()

        # Step 5 — Upsert to Chroma
        metadatas = [
            {
                "material_id": material.id,
                "course_id": material.course_id or "",
                "page": chunk.page if chunk.page is not None else -1,
                "chunk_index": chunk.chunk_index,
                "type": material.type or "",
            }
            for chunk in chunks
        ]
        rag.upsert_chunks(
            course_id=material.course_id or "",
            chunk_ids=chunk_ids,
            contents=contents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        # Step 6 — Extract concepts
        gateway = LLMGateway()
        concepts = extractor_svc.extract_concepts(markdown, gateway)

        # Step 7 — Write concepts to DB
        for concept in concepts:
            concept_id = str(uuid.uuid4())
            db_concept = Concept(
                id=concept_id,
                course_id=material.course_id,
                name=concept.name,
                type=concept.type,
                summary=concept.summary,
                # source_pages schema: [{material_id, pages: [int]}]
                source_pages=[{"material_id": material.id, "pages": concept.source_pages}],
                prerequisites=[],
                target_bloom=None,
                importance=None,
            )
            db.add(db_concept)
            created_concept_ids.append(concept_id)
        db.flush()

        # Step 8 — Mark indexed
        material.indexed = True
        db.commit()

        duration_ms = round((time.monotonic() - t0) * 1000)
        logger.info(
            "ingest_complete",
            extra={
                "material_id": material.id,
                "chunks_created": len(chunks),
                "concepts_extracted": len(concepts),
                "total_duration_ms": duration_ms,
            },
        )
        return IngestResult(
            chunks=len(chunks),
            concepts=len(concepts),
            duration_ms=duration_ms,
        )

    except Exception as exc:
        # Rollback DB rows created in this run
        db.rollback()
        _cleanup_chroma(rag, material.course_id or "", material.id)
        step = exc.step if isinstance(exc, IngestError) else "unknown"
        raise IngestError(str(exc), step=step) from exc


def _cleanup_chroma(rag: RAGService, course_id: str, material_id: str) -> None:
    try:
        rag.delete_material(course_id, material_id)
    except Exception as exc:
        logger.warning("rollback_chroma_failed", extra={"error": str(exc)})
