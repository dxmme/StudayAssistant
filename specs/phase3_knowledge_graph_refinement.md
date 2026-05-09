# Spec: Knowledge Graph Refinement (Phase 3.3)

> Status: `draft`
> Phase: 3
> Verwandte Research: [research/06_implementation_roadmap.md](../research/06_implementation_roadmap.md) · [research/04_system_architecture.md](../research/04_system_architecture.md)

## Ziel

Wenn Karten eines Konzepts wiederholt schlecht bewertet werden (viele Rating-1), schlägt das System neue Karten-Varianten vor — entweder automatisch erkannt oder manuell angestoßen. Der User sieht eine Review-Queue und entscheidet pro Vorschlag: annehmen, bearbeiten oder ablehnen. Alte Karten bleiben bestehen bis der User sie selbst archiviert.

## Nicht-Ziel

- Kein Auto-Archiv schlechter Karten (User entscheidet immer selbst)
- Keine Änderung von ConceptEdge-Kanten (Graph-Topologie bleibt unberührt)
- Kein Auto-Apply: generierte Karten werden nie direkt gespeichert ohne User-Approval
- Kein Batch-Refinement mehrerer Konzepte auf einmal (Queue, nicht Bulk-Job)
- Keine Neugenerierung von Konzepten selbst (nur Karten)
- Kein Gamification / Fortschritts-Streak für Refinements
- Kein Cronjob / Background-Task (Detection on-demand, nicht scheduled)

## Akzeptanzkriterien

- [ ] `GET /api/concepts/{concept_id}/refinement-status` gibt zurück ob Konzept Refinement-Kandidat ist (auto-Kriterium: ≥ 3 Rating-1 in letzten 14 Tagen) plus Anzahl `again_count`
- [ ] `POST /api/concepts/{concept_id}/refinements` startet Refinement: LLM generiert 3–5 neue Karten-Vorschläge; Response enthält `RefinementProposal`-Objekt mit Status `pending`
- [ ] Existierender `pending`-Proposal für Konzept: zweiter POST gibt 400 zurück (kein Duplikat)
- [ ] `GET /api/refinements?status=pending` gibt alle offenen Proposals zurück (für Review-Queue)
- [ ] `PATCH /api/refinements/{proposal_id}/cards/{card_index}/approve` erstellt neue Card in DB (wie normales Card-Create)
- [ ] `PATCH /api/refinements/{proposal_id}/cards/{card_index}/reject` markiert Card-Vorschlag als `rejected`
- [ ] `PATCH /api/refinements/{proposal_id}/cards/{card_index}/approve` erlaubt optionalen `question`/`answer`-Override (User-Edit vor Approve)
- [ ] Wenn alle Cards eines Proposals approved oder rejected: `RefinementProposal.status` → `completed`
- [ ] Manueller Trigger: Button "Konzept remixen" in Concept-Detail-View → `POST /api/concepts/{id}/refinements` (unabhängig vom Auto-Kriterium)
- [ ] Auto-Indikator in Concept-Graph-View: Konzepte mit `again_count ≥ 3` in letzten 14 Tagen erhalten visuellen Badge ("Refinement empfohlen")
- [ ] `pytest -m "not live"` grün, `npm test` + `npm run build` grün

## Datenmodell-Änderungen

### Neue Tabelle `refinement_proposals`

```sql
-- Migration XXXX_refinement_proposals (render_as_batch=True)
CREATE TABLE refinement_proposals (
    id          TEXT PRIMARY KEY,
    concept_id  TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    status      TEXT NOT NULL DEFAULT 'pending',   -- 'pending' | 'completed'
    cards       JSON NOT NULL,                      -- list[ProposedCard]
    again_count INTEGER,                            -- Snapshot zum Erstellungszeitpunkt
    created_at  TEXT NOT NULL,
    completed_at TEXT
);
```

```python
# models/refinement_proposals.py
class RefinementProposal(Base):
    __tablename__ = "refinement_proposals"
    id:           Mapped[str]      = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    concept_id:   Mapped[str]      = mapped_column(String(36), ForeignKey("concepts.id", ondelete="CASCADE"))
    status:       Mapped[str]      = mapped_column(String, default="pending")
    cards:        Mapped[list]     = mapped_column(JSON, nullable=False, default=list)
    again_count:  Mapped[int|None] = mapped_column(Integer, nullable=True)
    created_at:   Mapped[str]      = mapped_column(String, nullable=False)
    completed_at: Mapped[str|None] = mapped_column(String, nullable=True)
```

### ProposedCard-Format (JSON-Schema der `cards`-Spalte)

```json
[
  {
    "index": 0,
    "question": "Was ist der geometrische Sinn der VC-Dimension?",
    "answer": "Die VC-Dimension misst die Komplexität einer Hypothesenklasse...",
    "rationale": "Perspektive: geometrisch — alternative Sichtweise zur algebraischen Karte",
    "card_status": "pending"   // 'pending' | 'approved' | 'rejected'
  }
]
```

## API-Änderungen

### `GET /api/concepts/{concept_id}/refinement-status`

Prüft ob Konzept Refinement-Kandidat ist (on-demand, kein Cache).

```
GET /api/concepts/{concept_id}/refinement-status

Response 200:
{
  "concept_id": "uuid",
  "again_count": 5,
  "is_candidate": true,        // again_count >= 3 in letzten 14 Tagen
  "pending_proposal_id": "uuid" | null
}

Response 404: { "detail": "Concept not found" }
```

**Logik:**
```python
cutoff = (datetime.utcnow() - timedelta(days=14)).isoformat()
again_count = db.scalar(
    select(func.count()).select_from(Review)
    .join(Card, Review.card_id == Card.id)
    .where(Card.concept_id == concept_id, Review.rating == 1,
           Review.reviewed_at >= cutoff)
)
```

### `POST /api/concepts/{concept_id}/refinements`

Startet Refinement: generiert Karten-Vorschläge via LLM.

```
POST /api/concepts/{concept_id}/refinements

Response 201:
{
  "id": "uuid",
  "concept_id": "uuid",
  "status": "pending",
  "cards": [ { "index": 0, "question": "...", "answer": "...", "rationale": "...", "card_status": "pending" }, ... ],
  "again_count": 5,
  "created_at": "2026-05-09T10:00:00"
}

Response 400: { "detail": "Pending proposal already exists for this concept" }
Response 404: { "detail": "Concept not found" }
```

**LLM-Generierungslogik:**
1. Lade `Concept` + alle aktiven Cards des Konzepts (nicht archiviert)
2. Hole RAG-Kontext: `rag_search(concept.name, course_id, top_k=5)`
3. Snapshot `again_count` (letzte 14 Tage, für Protokoll)
4. System-Block (gecacht, ephemeral):
   ```
   Du bist ein Didaktik-Experte für ML-Mathematik.
   Konzept: {concept.name}
   Beschreibung: {concept.description}
   Kursmaterial (Auszüge): {rag_chunks}

   Bestehende Karten (werden NICHT automatisch gelöscht):
   {existing_cards_summary}

   Generiere 3–5 neue Lernkarten-Vorschläge die ANDERE Perspektiven beleuchten:
   - Geometrische oder intuitive Sichtweise
   - Anwendungsbeispiel
   - Kontra-Beispiel / Abgrenzung
   - Verbindung zu anderen Konzepten

   Antworte als JSON-Array:
   [{"question": "...", "answer": "...", "rationale": "..."}]
   Nur JSON, kein Prosa drumherum.
   ```
5. Parse JSON → `ProposedCard`-Liste
6. Persistiere `RefinementProposal` mit `status="pending"`
7. `LLMGateway.complete(system_block, messages, tier="default")`

**Neue Dateien (Backend):**
- `backend/app/services/refinement_engine.py` — LLM-Generierung + Status-Check
- `backend/app/api/refinements.py` — Router
- `backend/app/api/schemas/refinements.py` — Pydantic-Schemas

### `GET /api/refinements?status=pending`

```
GET /api/refinements?status=pending

Response 200:
[
  {
    "id": "uuid",
    "concept_id": "uuid",
    "concept_name": "VC-Dimension",     // JOIN
    "course_name": "Statistical ML",    // JOIN
    "status": "pending",
    "cards": [...],
    "again_count": 5,
    "created_at": "..."
  }
]
```

### `PATCH /api/refinements/{proposal_id}/cards/{card_index}/approve`

```
PATCH /api/refinements/{proposal_id}/cards/{card_index}/approve
Request (optional):
{
  "question": "überschriebene Frage",    // optional: User-Edit
  "answer": "überschriebene Antwort"     // optional: User-Edit
}

Response 200:
{
  "created_card_id": "uuid",
  "proposal": { ...aktualisiertes Proposal... }
}

Response 404: { "detail": "Proposal or card not found" }
Response 409: { "detail": "Card already approved or rejected" }
```

**Logik:** Erstellt neue `Card` (wie `POST /api/cards`) mit FSRS-Initialstate. Setzt `cards[index].card_status = "approved"`. Falls alle Cards approved/rejected: `proposal.status = "completed"`, `completed_at = now()`.

### `PATCH /api/refinements/{proposal_id}/cards/{card_index}/reject`

```
PATCH /api/refinements/{proposal_id}/cards/{card_index}/reject

Response 200: { "proposal": { ...aktualisiertes Proposal... } }
Response 404: { "detail": "Proposal or card not found" }
```

## UI-Änderungen

### Neue Route `/refinement`

`frontend/app/refinement/page.tsx` — Server Component

### Neue Komponente `RefinementQueue.tsx`

Client Component. Zeigt alle `pending` Proposals aus `GET /api/refinements?status=pending`.

```
┌─────────────────────────────────────────────────────────────────┐
│  Refinement Queue                             2 offene Konzepte │
│  ───────────────────────────────────────────────────────────    │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  VC-Dimension  (Statistical ML)        5× "Again" / 14d  │  │
│  │  ───────────────────────────────────────────────────────  │  │
│  │                                                           │  │
│  │  Vorschlag 1:                                             │  │
│  │  F: Was ist der geometrische Sinn der VC-Dimension?       │  │
│  │  A: Die VC-Dimension misst die Komplexität...             │  │
│  │  Grund: Geometrische Perspektive                          │  │
│  │  [ ✓ Annehmen ] [ ✎ Bearbeiten ] [ ✗ Ablehnen ]         │  │
│  │                                                           │  │
│  │  Vorschlag 2:                         [pending]           │  │
│  │  F: Nenne ein Kontra-Beispiel für VC-Dim = d+2...         │  │
│  │  A: ...                                                   │  │
│  │  [ ✓ Annehmen ] [ ✎ Bearbeiten ] [ ✗ Ablehnen ]         │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

- "Bearbeiten" → Inline-Textarea für `question`/`answer` vor Approve
- Status-Badge pro Vorschlag: pending / approved / rejected
- Proposal-Karte verschwindet aus Queue wenn alle Cards entschieden

### Änderung in Graph-View (`/graph`)

Konzept-Knoten mit `again_count ≥ 3` in letzten 14 Tagen: oranges Badge "⚠ Refinement" sichtbar. Klick auf Badge → Link zu `/refinement` oder direkter Trigger.

Implementierungsweg: `GET /api/concepts/{id}/refinement-status` wird beim Graph-Load für jeden Knoten parallel abgefragt (oder: ein neuer `GET /api/courses/{id}/refinement-candidates` Bulk-Endpoint für Effizienz).

### Änderung in Concept-Detail (falls vorhanden) oder Card-Detail

Button "Konzept remixen" → `POST /api/concepts/{id}/refinements` → Redirect zu `/refinement`.

### Navigation

`/refinement`-Link in Nav (neben `/plan`, `/review`, `/coach`) — optional mit Badge-Count wenn Proposals offen.

## LLM-Calls

| Eigenschaft | Wert |
|---|---|
| Tier | `default` (claude-sonnet-4-6) — Karten-Generierung, kein Beweis |
| Prompt-Caching | System-Block gecacht (ephemeral) |
| RAG | Top-5 Chunks aus `rag_search` |
| Erwartete Input-Tokens | ~1500–3000 (Concept + bestehende Karten + RAG) |
| Erwartete Output-Tokens | ~500–1000 (JSON-Array mit 3–5 Karten) |
| JSON-Parsing | Robustes Parsing: `json.loads(response_text.strip())`, Fallback auf `[]` bei ParseError |

## Tests

### Backend (`backend/tests/test_refinement.py`)

- `test_refinement_status_candidate` — Concept mit ≥ 3 Again-Ratings in 14d → `is_candidate: true`
- `test_refinement_status_not_candidate` — weniger als 3 → `is_candidate: false`
- `test_refinement_status_old_ratings_ignored` — Ratings älter als 14d → nicht gezählt
- `test_create_proposal` — Mock LLM → 201, `cards` enthält 3–5 Einträge, alle `card_status: "pending"`
- `test_create_proposal_duplicate` — zweiter POST für selbes Concept → 400
- `test_create_proposal_concept_not_found` — unbekannte Concept-ID → 404
- `test_list_proposals_pending` — GET mit `status=pending` → nur offene Proposals
- `test_approve_card` — PATCH approve → neue Card in DB, `card_status: "approved"`
- `test_approve_card_with_override` — PATCH mit `question`/`answer` → neue Card mit überschriebenen Werten
- `test_reject_card` — PATCH reject → `card_status: "rejected"`, keine neue Card
- `test_proposal_completed_when_all_decided` — alle Cards approved/rejected → `proposal.status: "completed"`
- `test_approve_already_decided` — approve auf bereits approved Card → 409
- `test_manual_trigger_below_threshold` — POST ohne Kandidaten-Kriterium → 201 (manuell immer möglich)

### Frontend (`frontend/tests/refinement.test.tsx`)

- `test_renders_pending_proposals` — gemockte API → Proposal-Karte sichtbar
- `test_approve_calls_patch` — Klick "Annehmen" → PATCH aufgerufen, Card verschwindet aus Queue
- `test_reject_calls_patch` — Klick "Ablehnen" → PATCH aufgerufen
- `test_edit_mode_textarea` — Klick "Bearbeiten" → Textareas für question/answer sichtbar
- `test_empty_queue_message` — keine Proposals → "Keine offenen Refinements"

## Offene Fragen

- `GET /api/courses/{id}/refinement-candidates` als Bulk-Endpoint für Graph-View statt N Einzel-Requests? → Annahme: Ja, effizienter; gibt alle Concept-IDs mit `again_count ≥ 3` für einen Kurs zurück.
- Falls LLM-JSON-Parsing fehlschlägt (invalides JSON): Vorschlag-Array leer lassen und 200 zurückgeben, oder 500? → Annahme: Log + 500 mit `{ "detail": "LLM returned invalid JSON" }` — User kann erneut triggern.
- Soll "Konzept remixen" auch erreichbar sein ohne Concept-Detail-Seite? → Ja, via Graph-View-Badge und `/refinement`-Queue-Link.
