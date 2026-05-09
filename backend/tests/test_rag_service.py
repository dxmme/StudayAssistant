from unittest.mock import patch

import pytest

from app.services.rag import ChunkHit, RAGService


def _make_rag() -> RAGService:
    """Create RAGService with in-memory Chroma (no disk, no telemetry)."""
    import chromadb

    client = chromadb.EphemeralClient()
    return RAGService(chroma_client=client)


def _fake_embed(texts: list[str]) -> list[list[float]]:
    """Deterministic embeddings: hash-based unit vectors in 4D."""
    import hashlib

    vectors = []
    for t in texts:
        h = int(hashlib.md5(t.encode()).hexdigest(), 16)
        raw = [(h >> (i * 8)) & 0xFF for i in range(4)]
        norm = sum(v**2 for v in raw) ** 0.5 or 1.0
        vectors.append([v / norm for v in raw])
    return vectors


_COURSE = "course-abc"
_MAT_A = "mat-001"
_MAT_B = "mat-002"

_CHUNKS = [
    {"id": "c1", "text": "SVD decomposes A into U Sigma V^T", "page": 1, "material_id": _MAT_A},
    {"id": "c2", "text": "Eigenvalues satisfy A v = lambda v", "page": 2, "material_id": _MAT_A},
    {"id": "c3", "text": "PCA uses SVD for dimensionality reduction", "page": 3, "material_id": _MAT_A},
    {"id": "c4", "text": "Gradient descent minimizes the loss", "page": 4, "material_id": _MAT_B},
    {"id": "c5", "text": "Backpropagation computes gradients", "page": 5, "material_id": _MAT_B},
]


@pytest.fixture
def rag_with_data():
    rag = _make_rag()
    embeddings = _fake_embed([c["text"] for c in _CHUNKS])
    rag.upsert_chunks(
        course_id=_COURSE,
        chunk_ids=[c["id"] for c in _CHUNKS],
        contents=[c["text"] for c in _CHUNKS],
        embeddings=embeddings,
        metadatas=[
            {"material_id": c["material_id"], "page": c["page"], "course_id": _COURSE, "chunk_index": i, "type": "lecture_slides"}
            for i, c in enumerate(_CHUNKS)
        ],
    )
    return rag


def test_upsert_and_search(rag_with_data):
    rag = rag_with_data
    with patch("app.services.embedder.embed_texts", side_effect=_fake_embed):
        # Query that semantically matches SVD-related chunks
        hits = rag.search(_COURSE, "SVD decomposition", k=3)
    assert len(hits) >= 1
    assert all(isinstance(h, ChunkHit) for h in hits)
    assert all(0.0 <= h.score <= 1.0 for h in hits)


def test_search_returns_at_most_k(rag_with_data):
    rag = rag_with_data
    with patch("app.services.embedder.embed_texts", side_effect=_fake_embed):
        hits = rag.search(_COURSE, "query", k=2)
    assert len(hits) <= 2


def test_search_empty_collection():
    rag = _make_rag()
    # Use a course ID that was never populated — works even if EphemeralClient shares process state
    with patch("app.services.embedder.embed_texts", side_effect=_fake_embed):
        hits = rag.search("empty-course-never-populated", "query", k=5)
    assert hits == []


def test_delete_material_removes_only_target(rag_with_data):
    rag = rag_with_data
    rag.delete_material(_COURSE, _MAT_A)

    # After deleting MAT_A, only MAT_B chunks remain
    col = rag._collection(_COURSE)
    remaining = col.get(where={"material_id": _MAT_B})
    assert len(remaining["ids"]) == 2  # c4, c5

    # MAT_A chunks gone
    gone = col.get(where={"material_id": _MAT_A})
    assert len(gone["ids"]) == 0


def test_delete_nonexistent_material_no_error():
    rag = _make_rag()
    # Should not raise, even if the collection or material doesn't exist
    rag.delete_material(_COURSE, "nonexistent")


def test_upsert_idempotent(rag_with_data):
    rag = rag_with_data
    # Re-upsert same chunks — should not duplicate
    embeddings = _fake_embed([_CHUNKS[0]["text"]])
    rag.upsert_chunks(
        course_id=_COURSE,
        chunk_ids=[_CHUNKS[0]["id"]],
        contents=[_CHUNKS[0]["text"]],
        embeddings=embeddings,
        metadatas=[{"material_id": _MAT_A, "page": 1, "course_id": _COURSE, "chunk_index": 0, "type": "x"}],
    )
    col = rag._collection(_COURSE)
    all_ids = col.get()["ids"]
    assert len(all_ids) == len(_CHUNKS)  # no duplicate
