# Spec: Plan Engine

> Status: `draft`
> Phase: 2
> Verwandte Research: [research/04_system_architecture.md](../research/04_system_architecture.md) · [research/05_ui_ux_design.md](../research/05_ui_ux_design.md)

## Ziel

Der User öffnet `/plan` und sieht für jeden Kurs einen generierten Tagesplan — mit fälligen Karteikarten, dem nächsten ungelernten Konzept und einer Coaching-Session — der automatisch auf sein Zeitbudget zugeschnitten ist. Items können abgehakt werden.

## Nicht-Ziel

- Quiz-Items, Worked-Example-Items, Mock-Exam-Items (kein Quiz-Service implementiert)
- Re-Planning nach Session (kein Post-Diagnostic-Trigger in Phase 2)
- Manuelles Concept-Ordering / Drag-and-Drop-Priorisierung
- Coaching-Diagnostic (triggert Card-Generierung) — Phase 3
- Mobile-Layout
- Gamification (XP, Streaks)

## Akzeptanzkriterien

- [ ] `POST /api/courses/{course_id}/plan/today` generiert einen Tagesplan und gibt ihn als JSON zurück (201)
- [ ] Zweiter POST am selben Tag gibt den existierenden Plan zurück ohne neues Objekt zu erstellen (200)
- [ ] `GET /api/courses/{course_id}/plan/today` gibt 200 + Plan falls vorhanden, 404 falls kein Plan für heute
- [ ] `PATCH /api/plans/{plan_id}/items/{item_index}/complete` setzt `items[index].done = true` und persistiert
- [ ] `POST /api/plans/{plan_id}/complete` setzt `status = "completed"` und `completed_at = now()`
- [ ] Phase-Bestimmung korrekt: `days_until_exam > 42` → `semester_companion`, `> 14` → `active_preparation`, `> 3` → `consolidation`, `<= 3` → `final_review`
- [ ] Kein `exam_date` → Fallback auf `semester_companion`
- [ ] Plan enthält `card_review`-Item nur wenn fällige Karten existieren; `new_concept`- und `coaching`-Items nur in `semester_companion` und `active_preparation`
- [ ] Nächstes Konzept wird topologisch gewählt: alle Prerequisite-Concepts müssen mastered sein (avg FSRS-Stability ≥ 21), dann sortiert nach `importance DESC`
- [ ] Konzept ohne Cards gilt als nicht mastered (zählt als zu lernen)
- [ ] Plan respektiert `UserPreferences.max_session_minutes` — Items werden weggelassen wenn Budget überschritten
- [ ] Kurs ohne Concepts: Plan enthält nur `card_review` (falls Cards existieren) oder leere Items-Liste
- [ ] `/plan` zeigt alle Kurse mit ihren Tagesplänen; Items sind abhakbar
- [ ] `pytest -m "not live"` grün, `npm test` + `npm run build` grün

## Datenmodell-Änderungen

Keine neue Migration nötig. `plan_sessions` und alle abhängigen Tabellen existieren bereits:

```sql
-- Bereits vorhanden (0001_initial_schema):
CREATE TABLE plan_sessions (
    id            TEXT PRIMARY KEY,
    course_id     TEXT REFERENCES courses(id) ON DELETE CASCADE,
    scheduled_date DATE,
    duration_min  INTEGER,
    items         JSON,          -- list[PlanItem] — siehe Item-Format unten
    status        TEXT NOT NULL, -- 'pending' | 'completed'
    completed_at  TEXT
);
```

### Item-Format (JSON-Schema der `items`-Spalte)

```json
[
  {
    "type": "card_review",
    "title": "25 fällige Karten",
    "estimated_min": 15,
    "done": false,
    "card_count": 25,
    "concept_id": null
  },
  {
    "type": "new_concept",
    "title": "VC-Dimension",
    "estimated_min": 10,
    "done": false,
    "card_count": null,
    "concept_id": "uuid-..."
  },
  {
    "type": "coaching",
    "title": "Coaching: VC-Dimension",
    "estimated_min": 15,
    "done": false,
    "card_count": null,
    "concept_id": "uuid-..."
  }
]
```

### Geschätzte Dauer pro Item-Typ (Konstanten im Service)

| Typ | Formel |
|---|---|
| `card_review` | `min(due_count, 30) * 2` Minuten |
| `new_concept` | 10 Minuten (flat) |
| `coaching` | 15 Minuten (flat) |

## API-Änderungen

### `POST /api/courses/{course_id}/plan/today`

Generiert Tagesplan oder gibt bestehenden zurück (idempotent).

```
POST /api/courses/{course_id}/plan/today

Response 201 (neu generiert):
{
  "id": "uuid",
  "course_id": "uuid",
  "scheduled_date": "2026-05-09",
  "duration_min": 40,
  "items": [...],
  "status": "pending",
  "completed_at": null
}

Response 200 (bereits vorhanden):
{ gleiche Struktur }

Response 404: { "detail": "Course not found" }
```

Generierungslogik:
1. Prüfe ob Plan für heute + `course_id` bereits existiert → 200 zurück
2. Lade `UserPreferences.max_session_minutes` (default 90)
3. Bestimme Phase aus `Course.exam_date` (Fallback: `semester_companion`)
4. Hole fällige Karten: `[c for c in cards if c.fsrs_state["due"] <= today_iso and not c.archived]`
5. Baue Items-Liste auf (Budget-Tracking):
   - Falls due_cards: `card_review`-Item hinzufügen; Budget -= estimated_min
   - Falls Phase `semester_companion` oder `active_preparation` und Budget >= 10:
     - `pick_next_concept()` — topologische Auswahl (siehe unten)
     - Falls Konzept gefunden: `new_concept`-Item hinzufügen; Budget -= 10
     - Falls noch Budget >= 15: `coaching`-Item für dasselbe Konzept hinzufügen; Budget -= 15
6. `duration_min` = Summe aller `estimated_min`
7. Persistiere `PlanSession` mit `status="pending"`, `scheduled_date=today`
8. Gib 201 zurück

### Concept-Auswahl-Logik (`pick_next_concept`)

```python
def pick_next_concept(course_id, db) -> Concept | None:
    concepts = db.scalars(select(Concept).where(
        Concept.course_id == course_id,
        Concept.archived == False  # falls archived später ergänzt wird; sonst weglassen
    )).all()

    # Mastery pro Concept: avg(stability) >= 21 über non-archived Cards
    def is_mastered(concept_id) -> bool:
        cards = db.scalars(select(Card).where(
            Card.concept_id == concept_id, Card.archived == False
        )).all()
        if not cards:
            return False
        stabilities = [c.fsrs_state.get("stability", 0) for c in cards if c.fsrs_state]
        if not stabilities:
            return False
        return (sum(stabilities) / len(stabilities)) >= 21.0

    mastered_ids = {c.id for c in concepts if is_mastered(c.id)}

    # Topologische Prüfung: alle Prerequisites mastered?
    def prereqs_done(concept) -> bool:
        edges = db.scalars(select(ConceptEdge).where(
            ConceptEdge.dst == concept.id,
            ConceptEdge.relation == "prerequisite"
        )).all()
        return all(e.src in mastered_ids for e in edges)

    candidates = [c for c in concepts if c.id not in mastered_ids and prereqs_done(c)]
    if not candidates:
        return None

    candidates.sort(key=lambda c: c.importance or 0.0, reverse=True)
    return candidates[0]
```

### `GET /api/courses/{course_id}/plan/today`

```
GET /api/courses/{course_id}/plan/today

Response 200: { gleiche Struktur wie POST }
Response 404: { "detail": "No plan for today" }   (auch wenn Course nicht existiert)
```

### `PATCH /api/plans/{plan_id}/items/{item_index}/complete`

```
PATCH /api/plans/{plan_id}/items/{item_index}/complete

Response 200: { gleiche PlanSession-Struktur mit items[item_index].done == true }
Response 404: { "detail": "Plan not found" }
Response 422: item_index out of range
```

Logik: Lade `PlanSession`, setze `items[item_index]["done"] = True`, persistiere.

### `POST /api/plans/{plan_id}/complete`

```
POST /api/plans/{plan_id}/complete

Response 200: { ..., "status": "completed", "completed_at": "2026-05-09T20:30:00" }
Response 404: { "detail": "Plan not found" }
```

### Neue Dateien (Backend)

- `backend/app/services/plan_engine.py` — Generierungslogik
- `backend/app/api/plans.py` — Router (prefix `/api/plans`)
- `backend/app/api/schemas/plans.py` — Pydantic-Schemas

Plan-Router wird in `main.py` ergänzt. `POST /api/courses/{id}/plan/today` und `GET /api/courses/{id}/plan/today` werden im `plans`-Router unter dem Courses-Prefix registriert.

### Pydantic-Schemas (`schemas/plans.py`)

```python
from typing import Literal
from pydantic import BaseModel
from datetime import date

class PlanItem(BaseModel):
    model_config = {"from_attributes": True}
    type: Literal["card_review", "new_concept", "coaching"]
    title: str
    estimated_min: int
    done: bool = False
    concept_id: str | None = None
    card_count: int | None = None

class PlanSessionResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    course_id: str | None
    scheduled_date: date | None
    duration_min: int | None
    items: list[PlanItem]
    status: str
    completed_at: str | None
```

## UI-Änderungen

### Neue Route

`frontend/app/plan/page.tsx` — Server Component

### Neue Komponenten

- `frontend/components/PlanDashboard.tsx` — Client Component; holt alle Kurse, generiert Pläne, rendert pro Kurs eine `PlanSessionCard`
- `frontend/components/PlanSessionCard.tsx` — Zeigt Kursname, Phase, Mastery-Anteil, Items-Liste
- `frontend/components/PlanItemRow.tsx` — Einzelnes Item mit Checkbox

### ASCII-Mock `/plan`

```
┌─────────────────────────────────────────────────────────────────┐
│  StudyAssistant · Tagesplan                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Statistical ML           Phase: Active Preparation       │  │
│  │  Klausur in 38 Tagen      40 min geplant                  │  │
│  │  ─────────────────────────────────────────────────────    │  │
│  │  [ ] Karteikarten-Review  25 fällige Karten   ~15 min    │  │
│  │  [ ] Neues Konzept        VC-Dimension         ~10 min    │  │
│  │  [ ] Coaching             Coaching: VC-Dim.    ~15 min    │  │
│  │                                                           │  │
│  │  [ Session abschließen ]                                  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Probabilistic ML         Phase: Semester Companion       │  │
│  │  Klausur in 47 Tagen      25 min geplant                  │  │
│  │  ─────────────────────────────────────────────────────    │  │
│  │  [ ] Neues Konzept        Bayesian Networks    ~10 min    │  │
│  │  [ ] Coaching             Coaching: Bayes.     ~15 min    │  │
│  │                                                           │  │
│  │  [ Session abschließen ]                                  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Verhalten

- `PlanDashboard` ruft beim Mount `POST /api/courses/{id}/plan/today` für jeden Kurs auf (idempotent)
- Checkbox-Klick → `PATCH /api/plans/{id}/items/{index}/complete` → lokaler State-Update
- "Session abschließen" → `POST /api/plans/{id}/complete` → Button deaktiviert, Status-Label "Abgeschlossen"
- Kurs ohne Plan-Items: Karte zeigt "Heute nichts fällig."
- Lade-State: Skeleton-Placeholder pro Kurs-Karte

### Navigation

`/plan`-Link in der bestehenden Nav (neben `/review`, `/coach`).

## LLM-Calls

Keine — Plan-Generierung ist reine Datenbanklogik.

## Tests

### Backend (`backend/tests/test_plan_engine.py`)

- `test_plan_creates_session` — POST für Kurs mit due Cards → 201, `status="pending"`, items enthält `card_review`
- `test_plan_idempotent` — zweiter POST → 200, gleiche `plan_id`
- `test_plan_get_today_existing` — GET nach POST → 200 + gleiche Daten
- `test_plan_get_today_none` — GET ohne vorherigen POST → 404
- `test_plan_no_exam_date_semester_companion` — Course ohne `exam_date` → `new_concept`-Item generiert (semester_companion)
- `test_plan_phase_active_preparation` — exam in 20 Tagen → `new_concept`-Item generiert
- `test_plan_phase_consolidation` — exam in 10 Tagen → kein `new_concept`, nur `card_review`
- `test_plan_phase_final_review` — exam in 2 Tagen → kein `new_concept`, nur `card_review`
- `test_plan_empty_curriculum` — Kurs ohne Concepts → nur `card_review` (falls Cards exist.)
- `test_plan_no_cards_no_concepts` — Kurs komplett leer → `items = []`, `duration_min = 0`
- `test_plan_concept_topological_order` — Concept B hat Prerequisite A (nicht mastered) → B wird nicht gewählt, A wird gewählt
- `test_plan_mastery_skip` — Concept mit avg stability 25 → gilt als mastered, wird übersprungen
- `test_plan_budget_trim` — `max_session_minutes = 15` → coaching-Item wird weggelassen
- `test_plan_mark_item_complete` — PATCH Item 0 → `items[0].done == true`
- `test_plan_mark_item_out_of_range` — PATCH Item 99 → 422
- `test_plan_complete_session` — POST complete → `status="completed"`, `completed_at` nicht None
- `test_plan_course_not_found` — POST für unbekannten Course → 404

### Frontend (`frontend/tests/plan.test.tsx`)

- `test_renders_loading_state` — vor API-Antwort: Skeleton sichtbar
- `test_renders_plan_items` — nach gemocktem POST: Item-Titel im DOM
- `test_item_checkbox_calls_patch` — Klick auf Checkbox → fetch mit PATCH aufgerufen
- `test_complete_button_calls_post` — Klick auf "Abschließen" → fetch mit POST aufgerufen
- `test_empty_items_message` — `items = []` → "Heute nichts fällig." sichtbar

## Offene Fragen

- Soll `/plan` automatisch alle Kurse laden und Pläne generieren, oder erst nach explizitem Klick pro Kurs? (Annahme jetzt: auto-generieren beim Mount — idempotent, kein Schaden.)
- Soll `PlanSessionCard` direkt auf `/review` / `/coach` verlinken wenn der User ein Item anklickt (statt nur Checkbox)? (Out-of-Scope für 2.6, kann nachträglich ergänzt werden.)
- Wie wird Mastery-% in der Kurs-Karte berechnet (angezeigt als "Mastery 67%")? (Anteil gemasterter Concepts — unkritisch für diese Spec, kann Placeholder sein.)
