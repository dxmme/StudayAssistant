import logging
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ChunkHit:
    chunk_id: str
    content: str
    page: int | None
    material_id: str
    score: float


class RAGService:
    def __init__(self, chroma_client=None) -> None:
        if chroma_client is not None:
            self._client = chroma_client
        else:
            import chromadb  # type: ignore[import-untyped]

            self._client = chromadb.PersistentClient(path=settings.chroma_persist_dir)

    def _collection(self, course_id: str):  # type: ignore[return]
        return self._client.get_or_create_collection(
            name=f"course_{course_id}",
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_chunks(
        self,
        course_id: str,
        chunk_ids: list[str],
        contents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        col = self._collection(course_id)
        col.upsert(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=metadatas,
        )

    def delete_material(self, course_id: str, material_id: str) -> None:
        """Remove all chunks belonging to material_id from the course collection."""
        try:
            col = self._collection(course_id)
            col.delete(where={"material_id": material_id})
        except Exception as exc:
            logger.warning(
                "chroma_delete_failed",
                extra={"material_id": material_id, "error": str(exc)},
            )

    def search(self, course_id: str, query: str, k: int = 5) -> list[ChunkHit]:
        from app.services.embedder import embed_texts

        query_embedding = embed_texts([query])[0]
        col = self._collection(course_id)
        count = col.count()
        if count == 0:
            return []
        results = col.query(
            query_embeddings=[query_embedding],
            n_results=min(k, count),
            include=["documents", "metadatas", "distances"],
        )
        hits: list[ChunkHit] = []
        if not results["ids"] or not results["ids"][0]:
            return hits
        for chunk_id, doc, meta, dist in zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            hits.append(
                ChunkHit(
                    chunk_id=chunk_id,
                    content=doc,
                    page=meta.get("page"),
                    material_id=meta.get("material_id", ""),
                    score=1.0 - dist,  # cosine: distance→similarity
                )
            )
        return hits


# Module-level singleton (lazy init)
_rag_service: RAGService | None = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
