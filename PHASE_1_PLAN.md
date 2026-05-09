# Phase 1 — Material Ingestion + Lernkern (PLAN)

**Status:** 📋 ALL 5 SPECS DRAFTED — ready for approval & implementation
**Date:** 2026-05-08
**Builds on:** Phase 0 (DB Schema, FastAPI, LLMGateway, Frontend Skeleton)
**Stop-Light:** 🟡 Nutzbar mit manuellen Workarounds (siehe research/06)

---

## Ziel der Phase

Aus dem leeren Phase-0-Skelett wird ein **lernbares System**:
- PDFs hochladen, parsen, indexieren.
- Karten **manuell** anlegen (kein Auto-Generate yet).
- Daily-Review-UI mit FSRS-Scheduler.
- Sokratisches Coaching als Streaming-Chat mit RAG.

Akzeptanz-Kriterien aus research/06:
- 100 manuell angelegte Karten, 14 Tage Reviews, alle FSRS-Übergänge korrekt.
- Coaching-Session über 10 Turns ohne Bug.
- Material-Suche per Embedding liefert relevante Snippets.

---

## Spec-Übersicht

| # | Spec | Datei | Komponenten |
|---|---|---|---|
| 1.1 | Material-Upload + PDF-Parsing | [phase1_material_upload.md](specs/phase1_material_upload.md) | `marker-pdf`, REST-Endpoints, File-Storage |
| 1.2 | Ingest-Pipeline (Chunks + Embeddings + minimale Konzept-Extraktion) | [phase1_ingest_pipeline.md](specs/phase1_ingest_pipeline.md) | Chroma, OpenAI-Embeddings, RAGService |
| 1.3 | Karten-CRUD + FSRS-Scheduler | [phase1_cards_fsrs.md](specs/phase1_cards_fsrs.md) | `py-fsrs`, Review-API, Determinismus-Test |
| 1.4 | Daily-Review-UI | [phase1_review_ui.md](specs/phase1_review_ui.md) | Next.js Route, Tastatur 1-4, Markdown+KaTeX |
| 1.5 | Sokratisches Coaching | [phase1_socratic_coaching.md](specs/phase1_socratic_coaching.md) | SSE-Streaming, RAG-Kontext, Sonnet |

---

## Implementierungs-Reihenfolge

```
1.1 Material-Upload
     │
     ▼
1.2 Ingest-Pipeline ──────► (RAGService verfügbar)
     │                              │
     ▼                              │
1.3 Cards + FSRS                    │
     │                              │
     ▼                              │
1.4 Review-UI       1.5 Coaching ◄──┘ (braucht RAG)
```

- **1.1 zuerst** — alles andere braucht Materialien.
- **1.2 zweitens** — RAGService ist Voraussetzung für 1.5.
- **1.3 parallel zu 1.2 möglich** — keine Abhängigkeit.
- **1.4 nach 1.3.**
- **1.5 zuletzt** — braucht RAG (1.2) und ist die komplexeste Spec.

---

## Neue Dependencies (kumuliert)

### Backend
- `marker-pdf` (PDF→Markdown, Math-aware) — Spec 1.1, in `[ingest]` extras
- `tiktoken` (Token-Counting fürs Chunking) — Spec 1.2
- `openai` (nur Embeddings) — Spec 1.2, in `[ingest]` extras
- `chromadb` (schon in `[ingest]`) — Spec 1.2
- `py-fsrs` (Spaced Repetition) — Spec 1.3, Hauptdependency

### Frontend
- `react-markdown` — Spec 1.4
- `remark-math` — Spec 1.4
- `rehype-katex` — Spec 1.4

### Settings (neu)
- `OPENAI_API_KEY` (für Embeddings) — Spec 1.2
- `chroma_persist_dir` (default `data/chroma`) — Spec 1.2
- `embedding_model` (default `text-embedding-3-large`) — Spec 1.2

---

## Migrations

| # | Datei | Inhalt |
|---|---|---|
| 0002 | `0002_materials_uploaded_at_datetime.py` | `materials.uploaded_at` von `TEXT` → `DateTime` |
| 0003 | `0003_cards_reviews_datetime.py` | `cards.created_at`, `reviews.reviewed_at` → `DateTime` + Indizes |
| 0004 | `0004_coaching_started_at_datetime.py` | `coaching_sessions.started_at` → `DateTime` (ggf. mit 0002 zusammengelegt) |

Alle Phase-0-Tabellen bleiben unverändert in Struktur — nur Typ-Korrekturen.

---

## API-Surface nach Phase 1

```
# Courses
POST   /api/courses
GET    /api/courses
GET    /api/courses/{id}

# Materials
POST   /api/courses/{course_id}/materials
GET    /api/courses/{course_id}/materials
GET    /api/materials/{id}/markdown
DELETE /api/materials/{id}
POST   /api/materials/{id}/ingest
GET    /api/materials/{id}/chunks

# Concepts (read-only in Phase 1)
GET    /api/courses/{course_id}/concepts

# Cards
POST   /api/courses/{course_id}/cards
GET    /api/cards/{id}
PATCH  /api/cards/{id}
DELETE /api/cards/{id}
GET    /api/courses/{course_id}/cards
GET    /api/courses/{course_id}/cards/due
POST   /api/cards/{id}/review

# Coaching
POST   /api/coaching/sessions
POST   /api/coaching/sessions/{id}/turn        (SSE stream)
POST   /api/coaching/sessions/{id}/end
GET    /api/coaching/sessions/{id}
GET    /api/courses/{course_id}/coaching/sessions
```

---

## Frontend-Routen nach Phase 1

```
/                                  Home (Phase 0)
/review/[courseId]                 Daily-Review-UI (Spec 1.4)
/coach/[courseId]/[conceptId]      Sokratisches Coaching (Spec 1.5)
```

(Course-Liste, Material-Liste, Card-Liste sind in Phase 1 nicht vom UI abgedeckt — Backend-API reicht. Phase 2 ergänzt UI.)

---

## Was *nicht* in Phase 1 ist (wichtig)

Aus research/06 explizit ausgeschlossen — nicht versehentlich einbauen:
- ❌ Auto-Karten-Generierung (Phase 2)
- ❌ Self-Critique / Karten-Dedup (Phase 2)
- ❌ Knowledge-Graph-Edges, Bloom/Importance, Konzept-Review-UI (Phase 2)
- ❌ Plan-Engine (Phase 2)
- ❌ Coaching-Diagnostic + Mastery-Update (Phase 2)
- ❌ Quiz-Engine (Phase 2)
- ❌ Worked Examples, Beweis-Reconstruction (Phase 3)
- ❌ Mock Exams (Phase 4)
- ❌ Mobile-First, Voice-Mode, PWA (Phase 5)

---

## Akzeptanz-Verifikation (Ende Phase 1)

Konkrete Tests, die grün sein müssen:

- [ ] **Material-Roundtrip:** PDF hochladen → ingest → Konzepte vorhanden → RAG-Suche liefert sinnvolle Snippets.
- [ ] **Karten-Lifecycle:** 100 Karten via API anlegen, 14 Tage Reviews simulieren (Determinismus-Test), Endzustände matchen Snapshot.
- [ ] **Review-UI:** 5-Karten-Session vollständig per Tastatur (Playwright-Test).
- [ ] **Coaching:** 10-Turn-Session ohne Crash, Cache-Read im 2. Turn > 0.
- [ ] **Embedding-Suche:** „SVD"-Query gegen indexiertes ML-Skript liefert Top-5-Chunks aus relevanten Seiten.

---

## Risiken & Mitigation

| Risiko | Quelle | Mitigation |
|---|---|---|
| `marker-pdf` Modell-Download blockiert ersten Upload | Spec 1.1 | README-Hinweis, kein Hard-Timeout |
| OpenAI-Key fehlt → Ingest scheitert | Spec 1.2 | Klare 412-Fehlermeldung, Hinweis auf Setup |
| `py-fsrs`-Upgrade ändert Default-Parameter | Spec 1.3 | Determinismus-Snapshot als Canary |
| SSE-Connection-Drop mid-Stream | Spec 1.5 | Frontend Error-Toast, User schickt erneut |
| User baut statt zu lernen | research/06 | Phase 1 ist „benutzbar genug" — `Build-vs-Use-Trade-off` aus research/06 beachten |

---

## Geschätzter Aufwand

Aus research/06: 2-3 Wochen Solo, 15-25 h/Woche.

Aufschlüsselung:
- Spec 1.1: ~1-2 Tage
- Spec 1.2: ~3-4 Tage (Chroma + Embedding-Setup ist neu, Konzept-Extraktion-Prompt-Tuning)
- Spec 1.3: ~2 Tage (FSRS-Lib einbinden, Determinismus-Test setup)
- Spec 1.4: ~2 Tage
- Spec 1.5: ~3 Tage (SSE + Streaming + Sokrates-Prompt-Tuning)

**Total: ~11-13 Werktage.**

---

## Nächster konkreter Schritt

Sobald Specs approved sind:

```bash
cd /home/ichzahlalles/StudyAssistant

# 1. Dependencies hinzufügen (manuell pyproject.toml + package.json editieren)
cd backend && uv sync --all-extras
cd ../frontend && npm install react-markdown remark-math rehype-katex

# 2. Migration 0002 generieren (Datetime-Korrekturen)
cd ../backend
.venv/bin/alembic revision --autogenerate -m "datetime corrections for phase 1"
.venv/bin/alembic upgrade head

# 3. Spec 1.1 implementieren
#    - app/api/schemas/courses.py + materials.py
#    - app/api/courses.py + materials.py
#    - tests/test_courses_api.py + test_materials_api.py
#    - tests/fixtures/sample.pdf committen
```

---

*Stand: 2026-05-08. Specs draftet, Implementierung folgt nach Approval.*
