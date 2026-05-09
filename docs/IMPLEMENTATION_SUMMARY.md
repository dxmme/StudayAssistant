# StudyAssistant — Implementierungsübersicht

**Stand:** 2026-05-09  
**Commit:** `f495ebb` (Phase 3 abgeschlossen)  
**Tests:** 158 Backend · 49 Frontend · Build ✅ · mypy strict ✅ · ruff ✅

---

## Stack

| Bereich | Technologie |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic V2 |
| KI | Anthropic SDK, Prompt Caching, Tier-System (Haiku / Sonnet / Opus) |
| Vektordatenbank | ChromaDB + OpenAI Embeddings |
| Spaced Repetition | py-fsrs |
| Frontend | Next.js 16 (App Router), React 19, TypeScript strict, Tailwind 4 |
| Mathe-Rendering | KaTeX (Server-Side) + `react-markdown` + `remark-math` |
| Tests | pytest · Vitest + @testing-library/react |
| DB | SQLite (`data/sqlite/study.db`) |

---

## Phase 0 — Foundation ✅

Grundgerüst: Datenbank, API-Skeleton, Frontend-Skeleton, LLM-Gateway.

### Spec 0.1 — DB-Schema + Alembic
- 13 SQLAlchemy-Modelle: `courses`, `materials`, `concepts`, `cards`, `reviews`, `worked_examples`, `quiz`, `coaching`, `plans`, `mock_exams` + Junction-Tabellen
- Alembic mit `render_as_batch=True` für SQLite
- Migration `0001_initial_schema.py`

### Spec 0.2 — FastAPI Skeleton
- `GET /health` · `GET /me` (Stub)
- CORS-Middleware, Pydantic-Settings, JSON-strukturiertes Logging

### Spec 0.3 — Frontend Skeleton
- Next.js App Router, TypeScript strict + `noUncheckedIndexAccess`
- KaTeX Server-Side Rendering (`<Math tex="..." />`)
- Vitest + jsdom Testinfrastruktur

### Spec 0.4 — LLM Gateway
- `LLMGateway.complete(system, messages, tier, max_tokens)`
- Tier-Map: `cheap` → Haiku 4.5 · `default` → Sonnet 4.6 · `hard` → Opus 4.7
- Prompt Caching: System-Block mit `"cache_control": {"type": "ephemeral"}`
- Retry bei HTTP 529 (Overloaded): 3 Versuche, exponential backoff

---

## Phase 1 — Core Learning Loop ✅

PDF-Upload → Konzepte → Karten → Review → Coaching.

### Spec 1.1 — Material-Upload + PDF-Parsing
- `POST /api/courses` · `POST /api/courses/{id}/materials` (Multipart)
- `marker-pdf` für Math-aware PDF-Konvertierung, pymupdf als Fallback
- Modell: `Material` mit `file_path`, `file_type`, `uploaded_at`

### Spec 1.2 — Ingest-Pipeline
- Chunking: ~500 Token, Satz-Grenzen respektiert (`chunker.py`)
- OpenAI-Embeddings → ChromaDB (`rag.py`)
- LLM-Konzeptextraktion: Sonnet liest Chunks → JSON-Array von Konzeptnamen
- `POST /api/materials/{id}/ingest` startet die Pipeline

### Spec 1.3 — Karten-CRUD + FSRS
- `cards` Tabelle mit `front`, `back`, `fsrs_state` (JSON), `review_count`, `lapse_count`
- py-fsrs: `Card.to_dict()` / `from_dict()`, Rating 1–4
- `GET /api/review/due` gibt fällige Karten zurück (FSRS-Scheduling)
- `POST /api/cards/{id}/review` schreibt Review + aktualisiert fsrs_state

### Spec 1.4 — Daily Review UI
- `/review` Route: `ReviewSession.tsx` (Client Component)
- Tastaturkürzel 1–4 für Ratings, Karte aufdecken per Space/Enter
- `RatingBar.tsx` mit farbcodierten Buttons (Again / Hard / Good / Easy)
- `MarkdownMath.tsx`: react-markdown + remark-math + rehype-katex

### Spec 1.5 — Sokratisches Coaching
- `POST /api/coaching` startet eine Coaching-Session
- SSE-Streaming (`text/event-stream`) für Tutor-Antworten
- RAG-Kontext: 3 relevante Chunks aus Kursmaterial als Prompt-Kontext
- `CoachingSession.tsx`: Chat-UI mit Streaming-Darstellung

---

## Phase 2 — Intelligence Layer ✅

User-Profile, Dashboard, Analytik, Multi-Review, Graph-Visualisierung, Plan-Engine.

### Spec 2.1 — User Profiles & Preferences
- `user_preferences` Tabelle: `ui_language`, `daily_card_limit`, `review_order`, `theme`
- `GET /api/me/preferences` · `PATCH /api/me/preferences`
- `SettingsForm.tsx` mit sofortigem PATCH bei Änderung

### Spec 2.2 — Progress Dashboard
- `/dashboard` Server Component
- Aggregierte Stats: Karten gesamt, fällig heute, Reviews letzte 7 Tage, Lernstreak
- `GET /api/analytics/summary`

### Spec 2.3 — Analytics
- `GET /api/analytics/daily` — Reviews pro Tag (letzte 30 Tage)
- `GET /api/analytics/monthly` — Aggregation pro Monat
- Daten-Modell: Abfragen auf `reviews`-Tabelle mit GROUP BY date

### Spec 2.4 — Multi-Concept Review
- `POST /api/reviews/multi` — Review mehrerer Karten in einem Request
- Nützlich für Batch-Operationen aus dem Daily-Plan

### Spec 2.5 — Concept Graph Visualisierung
- `GET /api/concepts?course_id=…` mit Parent-Child-Beziehungen
- `ConceptGraph.tsx` (Client Component): SVG-basierter Graph
- Klick auf Knoten navigiert zur Konzept-Detailseite

### Spec 2.6 — Plan Engine
- `plan_engine.py`: Tägliche Session-Generierung via topologischer Sortierung + FSRS-Filter
- `POST /api/courses/{id}/plan/today` — idempotent (erstellt nur wenn keiner für heute existiert)
- `GET /api/courses/{id}/plan/today` · `PATCH /api/plans/{id}/items/{idx}/complete`
- `PlanDashboard.tsx`: Checkliste mit Live-Update

---

## Phase 3 — Advanced Features ✅

Worked Examples, Proof Checker, Knowledge Graph Refinement.

### Spec 3.1 — Worked Examples
- `POST /api/cards/{id}/worked-example` — on-demand, kein Storage
- LLM-Tier: `hard` (Opus 4.7) für vollständige Schritt-für-Schritt-Lösungen
- RAG-Kontext: 3 Chunks aus Kursmaterial als Grundlage
- `WorkedExampleModal.tsx`: öffnet nach Card-Flip, ESC zum Schließen, Spinner während Laden
- Trigger: "Lösung anzeigen"-Button erscheint nur in der `back`-Phase des Reviews

### Spec 3.2 — Proof Checker
- Neues DB-Modell `proof_attempts` + `proof_mode`-Flag auf `cards`
- `POST /api/cards/{id}/proof-check` — bewertet freien Text-Beweis
- LLM gibt strukturiertes Feedback: `correct: bool`, `feedback: str`, `hint: str`
- Multi-Turn: bis zu 5 Versuche pro Session, Feedback akkumuliert
- `/proof/[cardId]` Route: `ProofCheckerSession.tsx` mit Textarea + Feedback-Anzeige

### Spec 3.3 — Knowledge Graph Refinement
- **Trigger:** Konzept mit ≥ 3 "Again"-Ratings (Rating 1) innerhalb von 14 Tagen
- **Datenmodell:** `refinement_proposals` Tabelle mit JSON-Array von `ProposedCard`-Objekten
- **Service:** `refinement_engine.py` — `compute_again_count()` + `generate_proposed_cards()`
- **LLM:** Sonnet (default), System-Prompt mit RAG-Kontext + bestehenden Karten, fordert 3–5 neue Perspektiven (geometrisch, Anwendungsbeispiel, Gegenbeispiel, Konzeptverbindung)
- **Endpoints:**
  - `GET /api/concepts/{id}/refinement-status` — Again-Count + Kandidaten-Flag
  - `POST /api/concepts/{id}/refinements` — erstellt Proposal (400 wenn pending existiert)
  - `GET /api/refinements?status=pending` — Queue für Review
  - `PATCH /api/refinements/{id}/cards/{idx}/approve` — erstellt echte Card (FSRS-Initialstate), 409 wenn bereits entschieden
  - `PATCH /api/refinements/{id}/cards/{idx}/reject` — 409 wenn bereits entschieden
  - `GET /api/courses/{id}/refinement-candidates` — Bulk-Abfrage für Graph-View
- **Auto-Complete:** Proposal wechselt zu `completed` sobald alle Cards entschieden
- `/refinement` Route: `RefinementQueue.tsx` mit Inline-Edit (Frage/Antwort änderbar vor Approve)

---

## API-Übersicht

```
GET    /health
GET    /me
GET    /me/preferences
PATCH  /me/preferences

POST   /api/courses
GET    /api/courses
GET    /api/courses/{id}
POST   /api/courses/{id}/materials           # PDF-Upload
POST   /api/materials/{id}/ingest            # Ingest-Pipeline
GET    /api/courses/{id}/concepts
GET    /api/courses/{id}/refinement-candidates

GET    /api/concepts/{id}/refinement-status
POST   /api/concepts/{id}/refinements

GET    /api/refinements                      # ?status=pending
PATCH  /api/refinements/{id}/cards/{idx}/approve
PATCH  /api/refinements/{id}/cards/{idx}/reject

GET    /api/cards
POST   /api/cards
GET    /api/cards/{id}
POST   /api/cards/{id}/review
POST   /api/cards/{id}/worked-example
POST   /api/cards/{id}/proof-check

GET    /api/review/due
POST   /api/reviews/multi

POST   /api/coaching                         # SSE-Stream

GET    /api/analytics/summary
GET    /api/analytics/daily
GET    /api/analytics/monthly

POST   /api/courses/{id}/plan/today
GET    /api/courses/{id}/plan/today
PATCH  /api/plans/{id}/items/{idx}/complete
```

---

## Frontend-Routen

| Route | Beschreibung |
|---|---|
| `/` | Homepage |
| `/review` | Daily Review Session |
| `/coach` | Sokratisches Coaching |
| `/plan` | Tagesplan-Dashboard |
| `/refinement` | Refinement-Queue (Karten-Proposals reviewen) |
| `/proof/[cardId]` | Proof Checker für eine Karte |
| `/settings` | User-Einstellungen |
| `/courses` | Kurs-Übersicht |

---

## Datenbankschema (alle Tabellen)

| Tabelle | Beschreibung |
|---|---|
| `courses` | Kurse |
| `materials` | Hochgeladene PDFs |
| `concepts` | Konzepte (hierarchisch via `parent_id`) |
| `cards` | Lernkarten mit FSRS-State + `proof_mode`-Flag |
| `reviews` | Review-Historie (Rating 1–4) |
| `coaching_sessions` | Coaching-Dialoge |
| `plans` | Tägliche Lernpläne |
| `user_preferences` | UI-Einstellungen pro User |
| `proof_attempts` | Beweis-Versuche mit LLM-Feedback |
| `refinement_proposals` | Vorgeschlagene Karten-Sets (JSON) |

---

## Teststatus

```bash
# Backend
cd backend && uv run pytest -m "not live" -q
# → 158 passed

# Frontend
cd frontend && npm test
# → 49 passed

# Qualität
uv run mypy app/ --strict   # ✅ 0 errors
uv run ruff check app/       # ✅ 0 violations
npm run build                # ✅ Static export erfolgreich
```

---

## Verzeichnisstruktur (wesentliche Dateien)

```
StudyAssistant/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── cards.py · coaching.py · concepts.py · courses.py
│   │   │   ├── materials.py · me.py · plans.py · health.py
│   │   │   ├── proof_checker.py · refinements.py · worked_examples.py
│   │   │   └── schemas/
│   │   │       ├── cards.py · proof_checker.py · refinements.py
│   │   │       └── worked_examples.py
│   │   ├── db/models/
│   │   │   ├── cards.py · concepts.py · courses.py · materials.py
│   │   │   ├── plans.py · proof_attempts.py · refinement_proposals.py
│   │   │   ├── reviews.py · user_preferences.py
│   │   │   └── __init__.py
│   │   └── services/
│   │       ├── llm_gateway.py · llm_models.py
│   │       ├── chunker.py · embedder.py · rag.py · ingest.py
│   │       ├── concept_extractor.py · coaching_prompt.py
│   │       ├── plan_engine.py · refinement_engine.py
│   │       └── parse_service.py
│   ├── alembic/versions/      # 6 Migrationen
│   └── tests/                 # 23 Testdateien
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx · layout.tsx
│   │   ├── coach/ · courses/ · plan/ · proof/ · refinement/
│   │   ├── review/ · settings/
│   │   └── globals.css
│   ├── components/
│   │   ├── CardView.tsx · MarkdownMath.tsx · Math.tsx · RatingBar.tsx
│   │   ├── ReviewSession.tsx · CoachingSession.tsx · SettingsForm.tsx
│   │   ├── ConceptGraph.tsx · PlanDashboard.tsx
│   │   ├── ProofCheckerSession.tsx · RefinementQueue.tsx
│   │   └── WorkedExampleModal.tsx
│   ├── tests/                 # 10 Testdateien
│   └── types/
│
└── specs/                     # Alle Spec-Dokumente
```
