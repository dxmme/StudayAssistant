# Spec: Ingest-Pipeline (Chunks + Embeddings + Vector-Store + minimale Konzept-Extraktion)

> Status: `draft`
> Phase: 1
> Verwandte Research: [research/04_system_architecture.md](../research/04_system_architecture.md) §Pipelines.A, [research/06_implementation_roadmap.md](../research/06_implementation_roadmap.md) §Phase-1

## Ziel
Nach `POST /api/materials/{id}/ingest` ist das Markdown des Materials in semantische Chunks zerlegt, jeder Chunk ist embedded und in Chroma gespeichert (Collection pro Course), `material_chunks`-Rows existieren mit Original-Text. Eine **minimale** LLM-Konzept-Extraktion füllt die `concepts`-Tabelle (ohne User-Review-UI, ohne Knowledge-Graph-Edges). Eine Suchfunktion `search_chunks(course_id, query, k)` liefert Top-k-Snippets aus dem Vector-Store.

## Nicht-Ziel
- Keine Konzept-Dedup-Logik (Embedding-Similarity-Merge) — kommt in Phase 2.
- Kein User-Review-UI für extrahierte Konzepte (Phase 2).
- Keine Knowledge-Graph-Kanten (`concept_edges`) — Phase 2.
- Keine Bloom/Importance-Scores aus Altklausuren — Phase 2.
- Keine Karten-Generierung (Phase 2).
- Kein Re-Ingest bei geänderter Datei — User muss `DELETE` + neu hochladen.
- Kein lokales Embedding-Modell (`bge-m3`) — wir nutzen die Anthropic-Plattform-Voreinstellung; siehe Offene Fragen.

## Akzeptanzkriterien
- [ ] `POST /api/materials/{id}/ingest` ist idempotent: zweiter Aufruf bei `indexed=True` → 200 mit `{status: "already_indexed"}`. Erstaufruf bei `indexed=False` → 200 mit `{status: "indexed", chunks: N, concepts: M, duration_ms}`.
- [ ] Pipeline-Schritte (in dieser Reihenfolge):
  1. Markdown-Sidecar laden (`{course_id}/{material_id}.md`).
  2. Semantic Chunking ~500 Tokens mit ~50 Tokens Overlap; Heading-Bewahrung (Splits bevorzugt an `#`/`##`-Grenzen, nie mitten im LaTeX-Block `$$...$$`).
  3. Pro Chunk: Embedding via Embedding-Service (siehe unten).
  4. `material_chunks`-Rows schreiben (`content`, `page` aus Markdown-Page-Markern, `chunk_index`, `token_count`).
  5. In Chroma-Collection `course_{course_id}` upserten: `id = chunk_id`, `embedding`, `metadata = {material_id, course_id, page, chunk_index, type}`.
  6. Konzept-Extraktion: LLM-Call (`tier="cheap"` = Haiku) mit dem **gesamten Markdown** als User-Message und einem fix gecachten System-Prompt. Output strukturiertes JSON: `[{name, type, summary, source_pages: [int]}]`. Bei Material > 100k Tokens: chunkweise verarbeiten und Resultate konkatenieren.
  7. Pro extrahiertem Konzept: `concepts`-Row schreiben (UUID4-id, `course_id`, `name`, `type`, `summary`, `source_pages=[{material_id, pages}]`, `prerequisites=[]`, `target_bloom=null`, `importance=null`).
  8. `materials.indexed=True` setzen.
- [ ] `GET /api/materials/{id}/chunks?limit=N` liefert die ersten N Chunks (für Debugging).
- [ ] `GET /api/courses/{course_id}/concepts` liefert alle Konzepte des Course (zur Verifikation).
- [ ] Service-Funktion `RAGService.search(course_id: str, query: str, k: int = 5) -> list[ChunkHit]` existiert in `backend/app/services/rag.py`. `ChunkHit = {chunk_id, content, page, material_id, score}`.
- [ ] Strukturiertes Logging: `material_id`, `chunks_created`, `concepts_extracted`, `embedding_tokens`, `extraction_input_tokens`, `extraction_output_tokens`, `total_duration_ms`.
- [ ] Bei Fehler in Schritt 3-7: Rollback — alle in diesem Run angelegten `material_chunks` und `concepts` löschen, Chroma-Upserts dieses Material rückgängig (Delete by `metadata.material_id`), `indexed` bleibt `False`. Response `500 {error, step}`.

## Datenmodell-Änderungen
Tabellen `material_chunks` und `concepts` sind aus Phase 0 vorhanden.

Anpassungen:
- `material_chunks` braucht keine zusätzlichen Spalten.
- `concepts.source_pages` JSON-Schema fix dokumentieren (in Code-Kommentar): `[{material_id: str, pages: list[int]}]`.

Keine neue Migration nötig.

## API-Änderungen

```
POST /api/materials/{id}/ingest
Response: 200 {status: "indexed" | "already_indexed", chunks: int, concepts: int, duration_ms: int}
        | 404 (material not found)
        | 409 (markdown sidecar missing — must re-upload)
        | 500 {error, step}

GET /api/materials/{id}/chunks?limit=20
Response: 200 [{id, content, page, chunk_index, token_count}, ...]

GET /api/courses/{course_id}/concepts
Response: 200 [{id, name, type, summary, source_pages}, ...]
```

Service-API (intern):
```python
class RAGService:
    def search(self, course_id: str, query: str, k: int = 5) -> list[ChunkHit]: ...
    def delete_material(self, material_id: str) -> None: ...  # für Material-DELETE-Cleanup

@dataclass
class ChunkHit:
    chunk_id: str
    content: str
    page: int | None
    material_id: str
    score: float
```

`Material-DELETE` aus Spec 1.1 ruft jetzt zusätzlich `RAGService.delete_material(id)` auf.

## UI-Änderungen
Keine.

## LLM-Calls
- **Konzept-Extraktion:** `LLMGateway.complete(tier="cheap")` → Haiku.
  - System-Prompt (~1200 Tokens, gecacht): Anweisung zur strukturierten Konzept-Extraktion mit JSON-Schema. Schema-Validierung per Pydantic auf der Antwort.
  - User-Message: Markdown des Materials (oder Chunk-Batch).
  - `max_tokens=4096`.
  - Bei JSON-Parse-Fehler: 1 Retry mit „Reply ONLY with valid JSON matching the schema." als zusätzliche User-Message.
- **Embeddings:** Embedding-Service-Wahl siehe Offene Fragen. Default Phase 1: **OpenAI `text-embedding-3-large`** (in research/04 als Default genannt). `OPENAI_API_KEY` zu `Settings` ergänzen.

## Bibliotheken / Dependencies (neu)
- `chromadb` — schon in `[ingest]` extras.
- `tiktoken` — Token-Counting fürs Chunking.
- `openai` — nur für Embeddings (NICHT für Completion). In `[ingest]` ergänzen.
- `pydantic` — schon vorhanden, für JSON-Schema-Validierung der LLM-Antwort.

Settings-Erweiterung in `backend/app/core/config.py`:
```python
openai_api_key: str | None = None
chroma_persist_dir: str = "data/chroma"
embedding_model: str = "text-embedding-3-large"
```

## Tests
- Unit (`tests/test_chunking.py`):
  - Markdown mit zwei Headings + LaTeX-Block → erwartete Chunk-Zahl, Overlap stimmt, kein Split innerhalb von `$$...$$`.
  - Page-Marker (z. B. `<!-- page: 12 -->` aus marker-pdf) → `page` korrekt zugeordnet.
- Unit (`tests/test_concept_extraction.py`):
  - Mock `LLMGateway`, gibt fixiertes JSON zurück → `concepts`-Rows werden korrekt geschrieben.
  - Mock gibt invalid JSON → Retry-Pfad → bei zweitem Fehler: Rollback + Error.
- Unit (`tests/test_rag_service.py`):
  - In-Memory-Chroma. 5 Test-Chunks upserten, mit Mock-Embeddings (deterministische Vektoren). `search("query")` liefert erwartete Top-k.
  - `delete_material(id)` entfernt nur Chunks dieses Materials.
- Integration (`tests/test_ingest_e2e.py`, `@pytest.mark.live`):
  - Echtes Embedding (OpenAI) + echte Konzept-Extraktion (Anthropic Haiku) auf Sample-PDF aus Spec 1.1. Smoke-Test, dass die Pipeline durchläuft, ≥1 Konzept extrahiert wird, ≥3 Chunks angelegt werden.

## Offene Fragen
- **Embedding-Modell:** `text-embedding-3-large` (OpenAI, $0.13/1M, 3072 dim) vs. `bge-m3` (lokal, kostenlos, ~1k dim). research/04 nennt OpenAI als Phase-1-Default mit Privacy-Switch später. → Phase 1: OpenAI. Wenn später lokal: in Settings umschaltbar via `embedding_provider`-Field. **Falls User keinen OpenAI-Key hat:** klare Fehlermeldung beim Ingest-Aufruf, Hinweis auf Setup.
- **Chroma-Collection-Lifecycle:** Eine Collection pro Course (`course_{id}`). Bei Course-DELETE → Collection droppen. Wird in Phase 2 (Course-DELETE-Endpoint) ergänzt; Phase 1 hat keinen Course-DELETE.
- **Konzept-Dedup gegen existierende Konzepte des gleichen Course:** Spec sagt explizit kein Dedup in Phase 1. Folge: zweiter Material-Upload kann denselben Konzept-Namen erneut anlegen. User-Review in Phase 2 räumt auf.
- **Welcher Tokenizer fürs Chunking?** `tiktoken` `cl100k_base` ist OpenAI-spezifisch, aber gut genug als Approximation für Anthropic-Counts in Phase 1.
- **Page-Marker-Format aus marker-pdf:** muss verifiziert werden. Falls keine sauberen Marker → Page-Field bleibt `None`, Chunks ohne Page-Info.
