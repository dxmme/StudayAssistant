# 04 — Systemarchitektur

> Dieses Dokument beschreibt **wie** das System gebaut wird: Datenmodell, Pipelines, LLM-Integration, lokale-vs-Cloud-Entscheidungen.
> Annahme: Web-App, lokal lauffähig, Single-User (du). Erweiterbar zu Multi-User später.

---

## High-Level-Architektur

```
┌────────────────────────────────────────────────────────────────────┐
│                         Frontend (Web)                             │
│   Next.js / SvelteKit  ·  Tailwind  ·  KaTeX  ·  WebSpeech         │
└──────────────────────────┬─────────────────────────────────────────┘
                           │  REST + SSE
┌──────────────────────────▼─────────────────────────────────────────┐
│                          Backend (FastAPI)                         │
│ ┌─────────────────────────────────────────────────────────────┐    │
│ │ Domain Services                                             │    │
│ │  ├─ Course Service (CRUD Fächer, Materialien)               │    │
│ │  ├─ Ingest Pipeline (PDFs → Konzepte + Embeddings)          │    │
│ │  ├─ Plan Engine (Curriculum-Planer)                         │    │
│ │  ├─ Card Service (FSRS-Scheduling, CRUD Karten)             │    │
│ │  ├─ Recall Coach (Sokratisches LLM-Coaching)                │    │
│ │  ├─ Quiz Engine (Generierung + Bewertung)                   │    │
│ │  ├─ Worked Example Service (Faded Stages)                   │    │
│ │  ├─ Proof Verifier (LaTeX-Parser + Vergleich)               │    │
│ │  └─ Mock Exam Engine                                        │    │
│ └─────────────────────────────────────────────────────────────┘    │
│ ┌─────────────────────────────────────────────────────────────┐    │
│ │ Infra                                                       │    │
│ │  ├─ LLM Gateway (Anthropic + Fallback)                      │    │
│ │  ├─ Embedding Service                                       │    │
│ │  ├─ Code Sandbox (für Mini-Implementations)                 │    │
│ │  └─ Job Scheduler (FSRS-Optimizer, Plan-Updates)            │    │
│ └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────────────┐
│   SQLite/Postgres   ·   Vector Store (chroma/qdrant)               │
│   File Storage (PDFs, Bilder)                                      │
└────────────────────────────────────────────────────────────────────┘
```

---

## Datenmodell

### Entitäten

```sql
-- Fach / Modul
CREATE TABLE courses (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,           -- "Statistical Machine Learning"
    semester        TEXT,
    exam_date       DATE,
    exam_format     TEXT,                    -- z.B. "90min, 6 Aufgaben, Cheat-Sheet erlaubt"
    professor       TEXT,
    notes           TEXT,
    created_at      TIMESTAMP
);

-- Hochgeladene Materialien
CREATE TABLE materials (
    id              TEXT PRIMARY KEY,
    course_id       TEXT REFERENCES courses(id),
    type            TEXT,                    -- 'lecture_slides', 'script', 'past_exam', 'topic_overview'
    title           TEXT,
    file_path       TEXT,
    page_count      INTEGER,
    indexed         BOOLEAN DEFAULT FALSE,
    uploaded_at     TIMESTAMP
);

-- Aus Materialien extrahierte Konzepte (Knowledge Graph Nodes)
CREATE TABLE concepts (
    id              TEXT PRIMARY KEY,
    course_id       TEXT REFERENCES courses(id),
    name            TEXT,                    -- "SVD"
    type            TEXT,                    -- 'definition', 'theorem', 'algorithm', 'concept', 'derivation'
    summary         TEXT,                    -- 1-2 Sätze für Plan-Anzeige
    target_bloom    INTEGER,                 -- 1-6
    importance      REAL,                    -- 0-1, aus Altklausur-Frequenz
    prerequisites   JSON,                    -- ["linear_algebra", "eigenvalues"]
    source_pages    JSON                     -- [{"material_id": "...", "pages": [12, 13, 14]}]
);

-- Edges im Knowledge Graph
CREATE TABLE concept_edges (
    src             TEXT REFERENCES concepts(id),
    dst             TEXT REFERENCES concepts(id),
    relation        TEXT,                    -- 'prerequisite', 'specializes', 'related'
    PRIMARY KEY (src, dst, relation)
);

-- Karteikarten
CREATE TABLE cards (
    id              TEXT PRIMARY KEY,
    course_id       TEXT REFERENCES courses(id),
    concept_id      TEXT REFERENCES concepts(id),
    type            TEXT,                    -- 'basic', 'cloze', 'concept_diagram', 'derivation', 'proof_skeleton'
    front           TEXT,
    back            TEXT,
    bloom_level     INTEGER,
    fsrs_state      JSON,                    -- {stability, difficulty, last_review, due, ...}
    review_count    INTEGER DEFAULT 0,
    lapse_count     INTEGER DEFAULT 0,
    created_at      TIMESTAMP,
    archived        BOOLEAN DEFAULT FALSE
);

-- Reviews-History (für FSRS-Optimizer)
CREATE TABLE reviews (
    id              TEXT PRIMARY KEY,
    card_id         TEXT REFERENCES cards(id),
    reviewed_at     TIMESTAMP,
    rating          INTEGER,                 -- 1=Again, 2=Hard, 3=Good, 4=Easy
    elapsed_days    REAL,
    state_before    JSON,
    state_after     JSON
);

-- Worked Examples
CREATE TABLE worked_examples (
    id              TEXT PRIMARY KEY,
    course_id       TEXT REFERENCES courses(id),
    concept_id      TEXT REFERENCES concepts(id),
    title           TEXT,
    steps           JSON,                    -- siehe Schema in 03_techniques_and_tools.md
    user_stage      INTEGER DEFAULT 0        -- 0=Worked, 1=Faded I, 2=Faded II, 3=Free
);

-- Quiz-Fragen
CREATE TABLE quiz_questions (
    id              TEXT PRIMARY KEY,
    course_id       TEXT REFERENCES courses(id),
    concept_id      TEXT REFERENCES concepts(id),
    type            TEXT,                    -- 'mc', 'short', 'calc', 'analyze', 'compare'
    bloom_level     INTEGER,
    question        TEXT,
    answer          TEXT,                    -- Soll-Antwort
    grounding       JSON,                    -- Source pages
    user_flagged    BOOLEAN DEFAULT FALSE
);

-- Quiz-Attempts
CREATE TABLE quiz_attempts (
    id              TEXT PRIMARY KEY,
    question_id     TEXT REFERENCES quiz_questions(id),
    user_answer     TEXT,
    score           REAL,                    -- 0-1
    feedback        TEXT,
    attempted_at    TIMESTAMP
);

-- Coaching-Sessions
CREATE TABLE coaching_sessions (
    id              TEXT PRIMARY KEY,
    course_id       TEXT REFERENCES courses(id),
    concept_id      TEXT REFERENCES concepts(id),
    transcript      TEXT,                    -- vollständig, für Diagnostic
    diagnostic      JSON,                    -- {gaps_identified: [...], mastered: [...], ...}
    duration_min    INTEGER,
    started_at      TIMESTAMP
);

-- Lernplan-Einheiten (Daily Sessions)
CREATE TABLE plan_sessions (
    id              TEXT PRIMARY KEY,
    course_id       TEXT REFERENCES courses(id),
    scheduled_date  DATE,
    duration_min    INTEGER,                 -- target
    items           JSON,                    -- [{type: 'cards', count: 30}, {type: 'concept', concept_id: 'svd'}, ...]
    status          TEXT DEFAULT 'pending',  -- 'pending', 'in_progress', 'completed', 'skipped'
    completed_at    TIMESTAMP
);

-- Mock Exams
CREATE TABLE mock_exams (
    id              TEXT PRIMARY KEY,
    course_id       TEXT REFERENCES courses(id),
    based_on        TEXT,                    -- past_exam material_id, or 'generated'
    started_at      TIMESTAMP,
    submitted_at    TIMESTAMP,
    duration_min    INTEGER,
    answers         JSON,
    score           REAL,
    breakdown       JSON                     -- pro Konzept Score
);
```

### Vektor-Storage (chroma/qdrant)

Pro Fach eine Collection:
- **Material-Chunks** (~500 Tokens) mit Metadata `{material_id, page, course_id, type}`.
- **Konzept-Embeddings** für Dedup-Detection.
- **Karten-Embeddings** für Dedup beim Generieren.

---

## Pipelines

### A. Material-Ingest-Pipeline

```
Upload PDF
   │
   ▼
[1] PDF → Markdown + LaTeX  
    (marker-pdf für Math-aware Konvertierung; pymupdf für Plain)
   │
   ▼
[2] Chunking (semantic, ~500 Tok mit Overlap)
   │
   ▼
[3] Embedding (text-embedding-3-large oder bge-m3)
   │
   ▼
[4] Vector-Store schreiben
   │
   ▼
[5] Konzept-Extraktion (LLM + Schema-Zwang)
    Prompt: "Extrahiere alle Definitionen, Sätze, Algorithmen, 
             zentrale Konzepte. Schema: {name, type, summary,
             prerequisites, source_pages}"
   │
   ▼
[6] Konzept-Dedup (Embedding-Similarity > 0.92 → merge)
   │
   ▼
[7] Knowledge-Graph aufbauen (LLM identifiziert Prerequisites)
   │
   ▼
[8] Bei Altklausur: Frage-Klassifikation (Bloom + Konzept-Tag)
    → updated importance scores in concepts table
   │
   ▼
[9] User Review: Konzept-Liste durchgehen, korrigieren
```

### B. Karteikarten-Generierung

```
Konzept ausgewählt
   │
   ▼
[1] RAG: hole relevante Snippets aus Vector-Store
   │
   ▼
[2] LLM-Prompt mit Konzept + Snippets + Card-Type-Templates
    Generiert 3-7 Vorschläge (Definition, Intuition, Beispiel, ...)
   │
   ▼
[3] Self-Critique: zweiter LLM-Call validiert (Andy-Matuschak-Regeln)
    - Atomic? Eine Idee?
    - Cloze am Satzende?
    - Front-Back nicht redundant?
    - Verbunden zu anderen Konzepten?
   │
   ▼
[4] Dedup gegen existierende Karten (Embedding-Similarity)
   │
   ▼
[5] User Review: akzeptieren / editieren / verwerfen
   │
   ▼
[6] Karten in DB schreiben, FSRS-State initialisieren
```

### C. Daily-Session-Generierung (Plan Engine)

Läuft jeden Morgen (oder beim ersten Öffnen):

```python
def generate_daily_session(user, course):
    today = date.today()
    days_until_exam = (course.exam_date - today).days
    
    # 1. Fällige Karten holen (FSRS)
    due_cards = get_due_cards(course, today)
    
    # 2. Phase bestimmen
    if days_until_exam > 42:    phase = "semester_companion"   # 60-80% neue Inhalte
    elif days_until_exam > 14:  phase = "active_preparation"   # 50% Recall, 50% neue
    elif days_until_exam > 3:   phase = "consolidation"        # 80% Recall, Mock Exams
    else:                        phase = "final_review"        # nur leichtes Review
    
    # 3. Plan-Items zusammenstellen
    items = []
    
    # Warm-up: Karten-Review (immer)
    items.append({"type": "card_review", "count": min(len(due_cards), 30)})
    
    # Neuer Content (phase-abhängig)
    if phase in ["semester_companion", "active_preparation"]:
        next_concept = pick_next_concept_from_curriculum(course, mastery_scores)
        items.append({"type": "new_concept", "concept_id": next_concept.id})
        items.append({"type": "worked_example", "concept_id": next_concept.id})
        items.append({"type": "coaching", "concept_id": next_concept.id, "duration_min": 15})
    
    # Quiz mit Interleaving
    weak_concepts = get_weakest_concepts(course, n=5)
    items.append({"type": "interleaved_quiz", "concepts": weak_concepts, "n_questions": 5})
    
    # Mock Exam (phase-abhängig)
    if phase in ["consolidation", "final_review"] and not mock_exam_today():
        if days_until_exam % 4 == 0:  # alle 4 Tage in Phase 3
            items.append({"type": "mock_exam", "duration_min": 90})
    
    # Reflexion
    items.append({"type": "reflection"})
    
    # Auf Tagesbudget zuschneiden
    items = trim_to_duration(items, user.daily_minutes)
    
    return PlanSession(course_id=course.id, scheduled_date=today, items=items)
```

### D. Coaching-Session-Pipeline (Streaming)

```
User wählt Konzept "SVD"
   │
   ▼
[1] RAG: hole Skript-Stellen, Vorlesungs-Foliennotation, ggf. Karten
   │
   ▼
[2] System-Prompt aufbauen (Sokrates + Kontext + Ziel-Bloom)
   │
   ▼
[3] LLM-Call (streaming) — Eröffnungsfrage
   │
   ▼
[4] User antwortet → LLM bewertet, stellt Folge-Frage
   │  (mehrere Runden)
   │
   ▼
[5] Nach 10-20 Min oder User beendet:
    [5a] LLM erstellt Diagnostic (separates Prompt)
    [5b] Diagnostic in DB
    [5c] Plan-Update-Trigger (gaps → cards/examples)
```

### E. Quiz-Bewertung

```
User reicht Antwort ein
   │
   ▼
[1] Question-Type erkennen
   │
   ├──► MC: exakt vergleichen, Score 0/1
   │
   ├──► Calc: numeric tolerance check (mit sympy für symbolisch)
   │
   └──► Free Text: 
        [a] LLM-Vergleich gegen Soll-Antwort + Kriterien
        [b] Score 0-1 + strukturiertes Feedback
        [c] Fehlende Punkte als FSRS-Rating-Hinweis
```

---

## LLM-Strategie

### Modell-Routing

| Task | Modell (Default) | Begründung | Kosten/1M Tok |
| --- | --- | --- | --- |
| Konzept-Extraktion (Ingest) | Claude Sonnet 4.6 | Strukturierte Outputs, 200k Context | $3 / $15 |
| Karten-Generierung | Claude Sonnet 4.6 | Qualität + Geschwindigkeit | $3 / $15 |
| Karten-Self-Critique | Claude Haiku 4.5 | Schnell, günstig, reicht | $1 / $5 |
| Sokratisches Coaching | Claude Sonnet 4.6 | Reasoning + Patience | $3 / $15 |
| Beweis-Verifikation | Claude Opus 4.7 | Schwierigste Reasoning-Aufgabe | $15 / $75 |
| Quiz-Generierung | Claude Sonnet 4.6 | Strukturierte Output, Nuance | $3 / $15 |
| Quiz-Bewertung (Free Text) | Claude Sonnet 4.6 | Genaue Bewertung wichtig | $3 / $15 |
| Embeddings | `text-embedding-3-large` (OpenAI) oder `bge-m3` (lokal) | Cost vs. Privacy | $0.13 / lokal |

### Prompt-Caching nutzen

- **System-Prompt + Kontext-Snippets** als `cache_control` markieren — bei wiederholten Calls (z. B. Coaching-Session, mehrere Quiz-Fragen zum gleichen Konzept) spart das massiv.
- Erwartete Einsparung: 60-80% bei mehrturnigen Sessions.

### Fallbacks

- LLM-Provider-Ausfall → Fallback auf zweiten Provider.
- Im "Offline-Modus": fällige Karten reviewen geht ohne LLM.

### Datenschutz

- **Default: lokal-first.** LLM-Calls gehen direkt vom Backend an Anthropic-API mit deinem Key — keine Drittfirmen.
- Optional: lokales LLM (Llama 3.x, Qwen) für Coaching wenn besondere Privacy-Anforderungen. Qualitäts-Tradeoff.

---

## Plan Engine — Curriculum-Logik

### Eingaben pro Fach

- Klausurdatum
- Tagesbudget (z. B. 90 min)
- Lerntage pro Woche (z. B. 5)
- Materialien (Folien, Skript, Altklausuren, Themenliste)

### Algorithmus (vereinfacht)

```python
def build_curriculum(course):
    concepts = topological_sort(course.concepts)        # Prerequisites zuerst
    weighted = weight_by_importance(concepts)           # Altklausur-Frequenz, Bloom-Spread
    
    total_days = working_days_until(course.exam_date)
    phases = allocate_phases(total_days)
    # phases = {semester_companion: D1, active_prep: D2, consolidation: D3, final: D4}
    
    plan = []
    
    # Phase 1: jeden Tag 1-2 neue Konzepte, 1 Worked Example, fällige Karten
    for day in range(phases["semester_companion"]):
        next_concepts = pick_next_due_concepts(weighted, day)
        plan.append(build_session(day, new=next_concepts, recall=due_cards(day)))
    
    # Phase 2: 50/50 neu/recall, mehr Quizzing, Interleaving
    for day in range(phases["active_prep"]):
        plan.append(build_session(day, ratio=(0.5, 0.5), interleaved_quiz=True))
    
    # Phase 3: 80% recall + Mock Exams alle 4 Tage
    for day in range(phases["consolidation"]):
        plan.append(build_session(day, ratio=(0.2, 0.8), mock_every=4))
    
    # Phase 4: nur leichtes Review
    for day in range(phases["final"]):
        plan.append(build_session(day, light_review=True))
    
    return plan
```

### Re-Planning (täglich)

Nach jeder Session:
- Aktualisiere mastery_scores aus Quiz-Performance + Coaching-Diagnostic.
- Berechne fällige Karten neu (FSRS).
- Verschiebe schlecht performte Konzepte nach vorne.
- Wenn ein Konzept *zu schwach* ist (mastery < 0.5 in Phase 3): rollback zu Worked Example, neue Karten generieren.

---

## Privacy & Local-First

| Aspekt | Empfehlung |
| --- | --- |
| **Materialien** | Nur lokal speichern. Niemals an externe Drittanbieter. |
| **LLM-Calls** | Direkt vom lokalen Backend an Anthropic. Keine Proxies. |
| **Vector-Store** | Lokal (chroma file-based). |
| **Backups** | User-eigene Backups (z. B. iCloud, Syncthing). System bietet `/export`. |
| **Telemetrie** | Keine. Keine Analytics. |

---

## Performance-Annahmen

- ~1000 Karten pro Fach realistisch.
- ~30 Reviews/Tag.
- Coaching-Session: ~3-5k Tokens pro Turn, 5-10 Turns → ~30-50k Tokens.
- Erwartete LLM-Kosten pro Lernsession: $0.10 - $0.50 (mit Caching).
- Erwartete Kosten pro Klausur-Vorbereitung (12 Wochen): $20 - $80.

---

## Erweiterungsmöglichkeiten (später)

- **Code-Sandbox** für Mini-Implementations (Python, sandboxed über `pyodide` oder Docker).
- **Whiteboard-Modus** für Beweis-Notation per Stylus / iPad.
- **Multi-User** mit Sharing-Mechanismus (Karten-Decks teilen anonymisiert).
- **Mobile App** (PWA reicht für Reviews unterwegs).
- **Spaced-Repetition für Code-Snippets** (Implementations-Patterns als „Karten").

---

*Stand: 2026-05-08. Architektur ist Vorschlag — Final-Decisions in `06_implementation_roadmap.md`.*
