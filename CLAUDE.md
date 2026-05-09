# StudyAssistant

Persönlicher Lernassistent für ML-Master Tübingen. Materialien rein → Lernplan + Active Recall + Spaced Repetition + Quizze + Sokratisches Coaching.

**Sprache:** Deutsch in Kommunikation. Englisch in Code, Commits, Logs, Docstrings.  
**Scope:** Alle Arbeit ausschließlich in `/home/ichzahlalles/StudyAssistant/`. Keine Dateien außerhalb.

---

## Stand

| Phase | Status | Tests |
|---|---|---|
| Phase 0 — Foundations | ✅ Complete (2026-05-08) | 7 backend / 2 frontend |
| Phase 1 — Lernkern | ✅ Complete (2026-05-09) | 99 backend / 17 frontend |
| Phase 2 — Analytics & Profile | 🔨 In Progress | 110 backend / 24 frontend |

**Quick-Start:**
```bash
cd backend && uv run pytest -m "not live" -q   # expect: 99 passed
cd frontend && npm test                         # expect: 17 passed
cd frontend && npm run dev                      # :3000
```

---

## Tech-Stack

### Backend
- Python 3.12 · FastAPI 0.136 · SQLAlchemy 2.x (`Mapped`-Syntax, kein `Column`) · Alembic 1.18 (`render_as_batch=True`) · Pydantic V2 (`SettingsConfigDict`) · SQLite (`data/sqlite/study.db`)
- Anthropic SDK 0.100 · Tenacity (Retry) · py-fsrs (Spaced Repetition) · Chroma (Vector DB, `data/chroma/`) · marker-pdf + pymupdf (PDF-Parsing)
- pytest · mypy --strict · ruff · black · uv

### Frontend
- Next.js 16.2 (App Router, kein src/) · React 19 · TypeScript strict + noUncheckedIndexAccess
- Tailwind 4 · KaTeX 0.16 (Server-Side via `<Math>`) · react-markdown 10+ (ESM-only) · remark-math · rehype-katex
- Vitest 4 + @testing-library/react + jsdom · Playwright (E2E) · npm

### LLM-Tier-System
```python
TIER_MODEL_MAP = {
    "default": "claude-sonnet-4-6",   # Coaching, Extraktion
    "cheap":   "claude-haiku-4-5-20251001",  # Bulk-Tasks
    "hard":    "claude-opus-4-7",     # Beweise, komplexe Sachverhalte
}
```

---

## Architektur

```
StudyAssistant/
  backend/app/
    api/          # FastAPI-Router (cards, coaching, health, materials, concepts, me)
    core/         # config.py (Pydantic Settings), logging.py (JSON-Logger)
    db/
      base.py     # DeclarativeBase
      models/     # 16 SQLAlchemy Models
    services/
      llm_gateway.py      # EINZIGER Anthropic-Einstiegspunkt
      llm_models.py       # Tier-Map
      coaching_prompt.py  # System-Prompt-Builder (Socratic rules + Concept + RAG)
      rag_search.py       # Chroma-basierte semantische Suche
      concept_extractor.py
  backend/alembic/versions/  # 0001_initial + 85dd8e6f264e_coaching_schema
  backend/tests/             # 99 Tests
  frontend/app/              # Next.js App-Router-Seiten
  frontend/components/       # ReviewSession, CoachingSession, MarkdownMath, CardView, ...
  frontend/tests/            # 17 Vitest-Tests
  frontend/tests-e2e/        # Playwright
  research/                  # READ-ONLY — Spec-Quelle für alle Implementierungen
  specs/                     # Task-Specs (Template: specs/TEMPLATE.md)
  data/                      # SQLite + Chroma + PDFs (.gitignore)
  .claude/commands/          # Slash-Commands
```

**Source of Truth:** Vor jeder Implementierung zuerst `research/` konsultieren — dann coden.

---

## Kritische Code-Patterns

Diese Patterns sind bindend. Abweichungen erzeugen Bugs.

### 1. SQLAlchemy 2.x — Mapped-Syntax
```python
# ✅ Richtig
from sqlalchemy.orm import Mapped, mapped_column
class Card(Base):
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    fsrs_state: Mapped[dict] = mapped_column(JSON, nullable=False)

# ❌ Falsch — SQLAlchemy 1.x Style
class Card(Base):
    id = Column(String(36), primary_key=True)
```

### 2. Pydantic V2 — Settings
```python
# ✅ Richtig
from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

# ❌ Falsch — Pydantic V1
class Settings(BaseSettings):
    class Config:
        env_file = ".env"
```

### 3. Alembic — SQLite Batch Mode
```python
# alembic/env.py — IMMER
context.configure(..., render_as_batch=True)
```

### 4. LLM Gateway — Einziger Einstiegspunkt
```python
# ✅ Richtig — immer über Gateway
from app.services.llm_gateway import LLMGateway
gw = LLMGateway()
response = gw.complete(system, messages, tier="default")

# ❌ Falsch — direkter API-Call
client = anthropic.Anthropic(api_key=...)
```

### 5. Prompt Caching — System als list[dict]
```python
# ✅ Richtig — system als Liste für Cache-Control
system_block = [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]
client.messages.create(model=model, system=system_block, messages=messages)
# Turn 1: cache_creation_input_tokens > 0
# Turn 2+: cache_read_input_tokens > 0

# ❌ Falsch — system als String (kein Caching)
client.messages.create(model=model, system="...", messages=messages)
```

### 6. FSRS — Scheduler-Konfiguration
```python
# Produktion — fuzzing für realistische Intervalle
scheduler = Scheduler()  # enable_fuzzing=True (default)

# Tests — IMMER deterministisch
scheduler = Scheduler(enable_fuzzing=False)
```

### 7. SSE Streaming — Buffer-Management
```python
# Backend: StreamingResponse mit text/event-stream
async def event_generator():
    for event in llm.complete_stream(system, messages):
        yield f"data: {json.dumps({'type': event.type, ...})}\n\n"
return StreamingResponse(event_generator(), media_type="text/event-stream")
```
```typescript
// Frontend: TextDecoder mit stream:true + Buffer
async function* parseSSE(response: Response) {
  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() ?? ''           // unvollständiges Event behalten
    for (const ev of events) {
      const line = ev.split('\n').find(l => l.startsWith('data: '))
      if (line) yield JSON.parse(line.slice(6))
    }
  }
}
```

### 8. KaTeX — Display vs. Inline
```typescript
// Inline-Mathe: $x^2$
// Display-Mathe: Dollar-Zeichen MÜSSEN auf eigener Zeile stehen
const displayMath = `$
\\sum_i x_i
$`  // → .katex-display Block

// ❌ Falsch — kein Display-Rendering
const wrong = `$\\sum_i x_i$`  // → nur .katex span (inline)
```

### 9. Vitest — ESM-Pakete (react-markdown v10+)
```typescript
// vitest.config.ts — MUSS alle ESM-only Deps inlinen
server: {
  deps: {
    inline: ['react-markdown', 'unified', 'remark-parse', 'remark-math',
             'remark-gfm', 'rehype-react', 'rehype-katex', 'hast-util-*',
             'unist-*', 'character-entities', /* ... 20+ total */]
  }
}
```

### 10. Soft Deletes & JSON-Filter
```python
# Alle Cards/Concepts: archived=False Filter IMMER mitgeben
query = select(Card).where(Card.course_id == course_id, Card.archived == False)

# Due-Date-Filter: Python-seitig, NICHT SQL (JSON-Embedded)
due_cards = [c for c in cards if c.fsrs_state["due"] <= today_iso]
```

---

## Workflow

**Reihenfolge ist bindend. Nie überspringen.**

### 1 — Alignment (vor jedem neuen Feature)
```
/grill-me <feature>
```
Claude interviewt systematisch: Datenmodell, API-Surface, Phase-Ausschlüsse, Edge Cases. Ziel: gemeinsames Verständnis vor dem ersten Commit.

### 2 — Spec schreiben
```
/spec <name>
```
Datei in `specs/<name>.md`. Template: `specs/TEMPLATE.md`. Kein Code vor Spec-Review.  
Pflicht: Akzeptanzkriterien (testbar!), Datenmodell-Auswirkungen, Out-of-Scope.

### 3 — Plan Mode (bei >3 betroffenen Dateien)
Plan Mode zeigt Dateiliste + Reihenfolge + Abhängigkeiten. Bestätigung vor Implementierung.

**Vertical Slices immer:**
```
✅ Migration + Service + Endpoint + Test für Feature A
❌ Erst alle Migrations, dann alle Services, dann alle Tests
```

### 4 — TDD-Implementierung
1. Failing Test schreiben → du bestätigst
2. Minimum-Implementierung für grünen Test
3. Refaktor falls nötig

**Feedback-Loops:**
```bash
# Backend
cd backend && uv run pytest tests/<test>.py -v
uv run mypy app/ --strict && uv run ruff check app/

# Frontend
cd frontend && npm test && npm run build
```

LLM-Unit-Tests: immer mock (kein API-Key). Live-Tests: `@pytest.mark.live` markieren.

### 5 — Review & Commit
```
/review   # Architektur-Checks
```
Manuelle UI-Tests bei Frontend-Touch. Dann:
```
<area>: <imperativer Titel max 60 Zeichen>

(optional: 1-3 Sätze WHY, nicht WHAT)
```
Areas: `backend` · `frontend` · `db` · `infra` · `docs` · `specs`

---

## Coding-Regeln

### Implementierungs-Disziplin
- **Spec-First.** Kein nicht-trivialer Code ohne `specs/<name>.md`.
- **Kein Auto-Save** generierter Inhalte (Karten, Konzepte) ohne User-Review-Queue.
- **YAGNI.** Keine Abstraktion die kein aktueller Task braucht.
- **Tests gehören zum Feature.** Nicht „später".

### Was NICHT tun
- ❌ Kein `Column(...)` — SQLAlchemy 2.x `Mapped[]` verwenden
- ❌ Kein `class Config:` — Pydantic V2 `SettingsConfigDict`
- ❌ Kein direkter `anthropic.Anthropic()` — `LLMGateway.complete()` verwenden
- ❌ Kein `system` als String — als `list[dict]` mit `cache_control`
- ❌ Kein `Scheduler()` in Tests — `Scheduler(enable_fuzzing=False)`
- ❌ Kein `any` in TypeScript — strict bleibt strict
- ❌ Kein `dangerouslySetInnerHTML` außerhalb `Math.tsx` / `MarkdownMath.tsx`
- ❌ Keine Gamification (XP, Streaks) — nie, auch nicht „weil ist nett"
- ❌ Keine Mobile-First-Annahmen — Desktop-first
- ❌ Keine eigene Spaced-Repetition-Logik — `py-fsrs` ist die Wahrheit

### Stil
- **Backend:** PEP8 · ruff · black · type hints überall · Docstrings nur wenn WHY nicht obvious
- **Frontend:** TS strict · Komponenten klein · benannt nach UX-Konzept
- **Naming:** Englisch · fachlich exakt (z. B. `Card.fsrs_state`, nicht `Card.metadata`)

### Token-Effizienz (Claude)
- Edit statt Write bei existierenden Dateien
- Glob/Grep zuerst, Read erst wenn Pfad klar
- Plan Mode für alles >3 Files
- Explore-Subagent für Suchen über >3 Stellen
- Keine langen Zusammenfassungen am Ende — max. 2 Sätze

---

## Session-Checkliste

**Vor jedem Task — kurz durchgehen:**

```
Alignment & Spec
[ ] Spec in specs/ vorhanden und reviewed?
[ ] Phase-2-Ausschlüsse nicht versehentlich eingebaut?

Datenmodell
[ ] Neue Migration nötig? (render_as_batch=True!)
[ ] FK mit ondelete="CASCADE"?
[ ] Mapped[]-Syntax (kein Column())?

Backend
[ ] Pydantic V2 (SettingsConfigDict)?
[ ] LLMGateway.complete() — nie direkter SDK-Call?
[ ] Richtiger Tier? (default/cheap/hard)
[ ] System-Block als list[dict] mit cache_control?
[ ] Kein Auto-Save generierter Inhalte?

Frontend
[ ] TypeScript strict — kein any?
[ ] Display-Mathe: $\n...\n$ (Dollar auf eigener Zeile)?
[ ] server.deps.inline für neue ESM-Deps in vitest?
[ ] scrollIntoView mit optional chaining (?.)? (jsdom fehlt API)

Tests
[ ] pytest -m "not live" grün?
[ ] npm test + npm run build grün?
[ ] Live-Tests mit @pytest.mark.live markiert?
[ ] Scheduler(enable_fuzzing=False) in FSRS-Tests?
```

---

## Slash-Commands

| Command | Zweck |
|---|---|
| `/grill-me <feature>` | Alignment-Interview vor Implementierung |
| `/spec <name>` | Neue Spec aus Template |
| `/phase-start <n>` | Phase n aus Roadmap initialisieren |
| `/write-a-prd <name>` | Konversation → PRD in `.claude/prds/` |
| `/write-issues <prd>` | PRD → Kanban-Issues in `.claude/issues/` |
| `/improve-arch` | Architektur-Verbesserungskandidaten finden |

---

## Domänen-Vokabular (Kurzreferenz)

| Begriff | Definition | Code |
|---|---|---|
| Course | ML-Vorlesung — Aggregationseinheit | `models/courses.py` |
| Material | Hochgeladenes PDF/Video | `models/materials.py` |
| Concept | Atomares Lernziel aus Material | `models/concepts.py` |
| Card | Frage-Antwort-Paar mit FSRS-State | `models/cards.py` |
| Review | Einzelne Beurteilung einer Card (Rating 1–4) | `models/reviews.py` |
| FSRS-State | JSON-Blob: stability, difficulty, due (py-fsrs) | `Card.fsrs_state` |
| Rating | 1=Again · 2=Hard · 3=Good · 4=Easy | `Review.rating` |
| CoachingSession | Sokratischer Dialog: Transcript + Metadata | `models/coaching.py` |
| Chunk | ~512-Token-Textsegment aus Material | Chroma-Einheit |
| RAG-Kontext | Top-5 Chunks als LLM-Prompt-Kontext | `rag_search.py` |
| Tier | LLM-Qualitätsstufe: default/cheap/hard | `llm_models.py` |
| Ingest-Pipeline | PDF → Text → Chunks → Embeddings → Chroma | Phase 1.2 |

Vollständiges Vokabular: `.claude/GLOSSARY.md`

---

## Bekannte Fallstricke

| Fehler | Fix |
|---|---|
| `Column(...)` statt `Mapped[]` | SQLAlchemy 2.x Syntax verwenden |
| `class Config:` statt `SettingsConfigDict` | Pydantic V2 migrieren |
| Kein `render_as_batch=True` | SQLite-Error bei ALTER TABLE |
| `system` als String | Als `list[dict]` mit `cache_control` |
| `Scheduler()` in Tests | `Scheduler(enable_fuzzing=False)` |
| `$\sum$` statt `$\n\sum\n$` | Display-Math braucht eigene Zeilen |
| Neue ESM-Dep nicht in `inline` | vitest kann jsdom nicht transformieren |
| `scrollIntoView()` ohne Guard | jsdom: `?.scrollIntoView?.({...})` |
| Direkter Anthropic-Call | `LLMGateway.complete()` verwenden |
| Auto-Save generierter Karten | Review-Queue einbauen, nie direkt speichern |
| JSON-Filter per SQL (fsrs due) | Python-seitig filtern (SQLite JSON-Dialekte) |
| Horizontales Slicing | Vertical Slices (Schema+Service+Test gemeinsam) |

---

## Phase 2 — Upcoming

Aus `research/06_implementation_roadmap.md`:
1. **Spec 2.1** — User Profiles & Preferences
2. **Spec 2.2** — Progress Dashboard (Charts, Stats)
3. **Spec 2.3** — Analytics (FSRS-Effektivität, Time-to-Mastery)
4. **Spec 2.4** — Multi-Concept Review (Batch-Reviews)
5. **Spec 2.5** — Concept Graph Visualization (Prereq-Beziehungen)

Start: `/grill-me phase-2` → `/spec <name>` → Implementierung.
