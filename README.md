# StudyAssistant

Ein KI-gestützter Lernbegleiter — gebaut auf dem aktuellen Stand der Lernwissenschaft.

Du lädst deine Vorlesungsfolien hoch. Das System extrahiert die Konzepte, generiert Lernkarten, plant deine täglichen Sessions, coacht dich sokratisch durch die Lücken — und verfeinert sich selbst, wenn du immer wieder an denselben Stellen scheitert.

**Kein Gamification. Kein Fluff. Nur was funktioniert.**

---

## Warum es funktioniert — wissenschaftlicher Hintergrund

Die vier Kernmechanismen des Systems haben die stärkste empirische Evidenz in der Lernforschung:

| Mechanismus | Effect Size | Quelle | Im System |
|---|---|---|---|
| **Retrieval Practice** | g = 0.50–0.61 | Rowland 2014, Adesope 2017 | Lernkarten, Coaching, Proof Checker |
| **Spaced Repetition** | Top-2 weltweit | Donoghue & Hattie 2021 (242 Studien, 169.000+ Probanden) | FSRS-Algorithmus |
| **Interleaving** | moderat–hoch | Dunlosky 2013 | Multi-Concept Review, Plan Engine |
| **Self-Explanation** | moderat | Chi et al. 1989, Dunlosky 2013 | Sokratisches Coaching |

### FSRS — Spaced Repetition auf ML-Basis

Der Scheduling-Algorithmus basiert auf **Free Spaced Repetition Scheduler (FSRS)**, trainiert auf 700 Millionen Anki-Reviews. Er berechnet für jede Karte individuell:

- **Stability** — wie lange du die Information behältst
- **Difficulty** — wie schwer dir das Konzept fällt
- **Due Date** — exakt wann die nächste Wiederholung den höchsten Lerneffekt hat

Das Resultat: Du wiederholst Karten kurz vor dem Vergessen — dem Punkt, an dem Abruf die Gedächtnisspur am stärksten festigt (Bjork: *Forgetting-Effort-Hypothesis*).

### Sokratisches Coaching — nicht Lösung, sondern Lücke

Das LLM gibt **niemals die Antwort**. Es legt den Finger in die Lücke:

```
Du:   "SVD ist stabiler weil A^T A symmetrisch ist"
Coach: "Aber A^T A ist immer symmetrisch — wo genau kommt die
        Stabilität her? Was passiert mit κ(A^T A) vs κ(A)?"
Du:   "Ah — die Konditionszahl quadriert sich bei A^T A..."
```

Dieses Prinzip erzwingt **tiefes Verarbeiten** statt oberflächliche Wiedererkennung. Studien zeigen, dass selbst generierte Erklärungen deutlich besser behalten werden als gelesene (Generation Effect).

### Warum Highlighting und Re-Reading nicht funktionieren

Laut Dunlosky et al. (2013) sind die meisten Standard-Lerntechniken ineffektiv:

| Technik | Utility | Warum |
|---|---|---|
| Highlighting | **low** | Passiv, keine Verarbeitung |
| Re-Reading | **low** | Vertrautheit ≠ Wissen |
| Zusammenfassungen schreiben | low–moderate | Skill-abhängig, selten effektiv |

Das System bietet diese Techniken bewusst **nicht** an.

---

## Features

### Implementiert (Phase 0–3)

- **PDF-Upload & Ingest** — marker-pdf parst math-aware, OpenAI-Embeddings in ChromaDB
- **Konzept-Extraktion** — LLM identifiziert atomare Lernziele aus deinem Material
- **Lernkarten mit FSRS** — Rating 1–4, adaptives Scheduling, Tastaturkürzel
- **Sokratisches Coaching** — SSE-Streaming, RAG-Kontext aus deinen PDFs, kein Antwort-Leaken
- **Tagesplan-Engine** — topologische Sortierung nach Konzept-Abhängigkeiten + FSRS-Filter
- **Progress Dashboard** — Reviews letzte 7 Tage, Fälligkeiten, Lernstreak
- **Analytics** — tägliche und monatliche Review-Statistiken
- **Concept Graph** — interaktive Visualisierung der Konzept-Hierarchie
- **Worked Examples** — On-demand LLM-Schritt-für-Schritt-Lösungen (Opus, nur auf Anfrage)
- **Proof Checker** — freie Texteingabe, LLM-Feedback + Hints, bis zu 5 Versuche
- **Knowledge Graph Refinement** — bei 3+ "Again"-Ratings generiert das System neue Kartenvorschläge aus anderen Perspektiven (geometrisch, Anwendung, Gegenbeispiel)
- **User Preferences** — Sprache, Tageslimit, Reihenfolge, Theme

### Noch nicht implementiert

- **Exam Mode** — Mock-Klausuren unter Zeitdruck (geplant für Phase 4)
- **Multi-User-Auth** — aktuell Single-User lokal
- **Mobile UI** — Desktop-First, kein responsives Layout

---

## Tech-Stack

| Bereich | Technologie |
|---|---|
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2.x · Alembic · Pydantic V2 |
| Datenbank | SQLite (lokal) · ChromaDB (Vektoren) |
| KI | Anthropic Claude (Haiku / Sonnet / Opus) · OpenAI Embeddings |
| Spaced Repetition | py-fsrs |
| Frontend | Next.js 16 (App Router) · React 19 · TypeScript strict · Tailwind 4 |
| Mathe | KaTeX (Server-Side) + remark-math + rehype-katex |
| Tests | pytest (158) · Vitest (49) |

---

## Installation

### Voraussetzungen

- Python 3.12+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Anthropic API Key](https://console.anthropic.com/) — **Pflicht**
- [OpenAI API Key](https://platform.openai.com/) — für Embeddings (optional, aber für Ingest-Pipeline benötigt)

### 1. Repository clonen

```bash
git clone <repo-url> StudyAssistant
cd StudyAssistant
```

### 2. Backend einrichten

```bash
cd backend

# Abhängigkeiten installieren (Basis + Ingest-Pipeline)
uv sync --extra ingest

# .env erstellen
cp .env.example .env
```

Öffne `.env` und trage deine Keys ein:

```env
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=sqlite:///./data/sqlite/study.db
ENVIRONMENT=development

# Für PDF-Ingest und Embeddings:
OPENAI_API_KEY=sk-...
```

```bash
# Datenbankverzeichnisse anlegen
mkdir -p data/sqlite data/chroma data/uploads

# Datenbank-Migrationen ausführen
uv run alembic upgrade head

# Backend starten
uv run uvicorn app.main:app --reload --port 8000
```

Backend läuft auf [http://localhost:8000](http://localhost:8000) — API-Docs unter [http://localhost:8000/docs](http://localhost:8000/docs).

### 3. Frontend einrichten

```bash
cd frontend  # aus dem Projektroot
npm install
npm run dev
```

Frontend läuft auf [http://localhost:3000](http://localhost:3000).

### Schnellstart ohne OpenAI

Wenn du keinen OpenAI-Key hast, kannst du trotzdem fast alles nutzen — nur die Ingest-Pipeline (PDF → Embeddings → ChromaDB) benötigt ihn. Karten und Coaching funktionieren auch ohne RAG-Kontext.

---

## Optimale Nutzung — Schritt für Schritt

### Schritt 1: Kurs anlegen

Gehe zu `/courses` → "Neuer Kurs". Name des Kurses, Klausurdatum eintragen.

Das Klausurdatum ist der **harte Eingabeparameter** für die Plan-Engine — sie plant rückwärts von diesem Datum.

### Schritt 2: PDFs hochladen und ingesten

Lade alle Vorlesungsfolien, Skripte oder Paper hoch (PDF). Klicke dann auf "Ingest" — dieser Schritt:

1. Parst das PDF math-aware (LaTeX-Formeln bleiben erhalten)
2. Zerlegt den Text in ~500-Token-Chunks
3. Erstellt OpenAI-Embeddings und speichert sie in ChromaDB
4. Lässt Claude die atomaren Konzepte extrahieren

Das dauert je nach Größe 1–5 Minuten. Einmal tun — danach sind alle Features verfügbar.

### Schritt 3: Lernkarten anlegen (oder generieren lassen)

Nach dem Ingest findest du unter `/courses/[id]/concepts` alle extrahierten Konzepte. Für jedes Konzept kannst du:

- Karten manuell anlegen (Frage/Antwort)
- Karten vom LLM vorschlagen lassen

**Tipp:** Eigene Karten funktionieren oft besser, weil du sie in deiner eigenen Sprache formulierst.

### Schritt 4: Tägliche Lernroutine

Der empfohlene Tagesablauf (45–60 Minuten):

#### 1. Daily Plan generieren (`/plan`)

Die Plan-Engine erstellt deinen Tagesplan basierend auf:
- Welche Karten heute fällig sind (FSRS)
- Topologische Reihenfolge der Konzepte (Grundlagen vor Aufbau)
- Deinem täglichen Kartenlimit (einstellbar in `/settings`)

#### 2. Review-Session (`/review`)

Karten einzeln durcharbeiten:

| Taste | Aktion |
|---|---|
| `Space` / `Enter` | Karte aufdecken |
| `1` | Again — habe es nicht gewusst |
| `2` | Hard — war schwer, aber richtig |
| `3` | Good — korrekt mit etwas Nachdenken |
| `4` | Easy — sofort gewusst |

**Wichtig:** Sei ehrlich bei den Ratings. Das System ist nur so gut wie deine Selbsteinschätzung.

> "Wenn du dich anstrengst, lernst du. Wenn alles flutscht, bist du auf zu leichtem Niveau."

#### 3. Coaching für schwierige Konzepte (`/coach/[courseId]/[conceptId]`)

Nach dem Review: Für Konzepte, bei denen du oft "Again" oder "Hard" gewählt hast, öffne eine Coaching-Session.

**Nicht fragen "Was ist X?" — sondern erklären:**

```
❌ "Erkläre mir was Backpropagation ist"
✅ "Ich erkläre dir Backpropagation: [deine Erklärung]... Stimmt das so?"
✅ "Ich verstehe nicht warum wir bei der Kettenregel von rechts nach links gehen"
```

Der Coach antwortet nie mit der Lösung — er fragt weiter, bis du sie selbst erarbeitest.

### Schritt 5: Worked Examples bei neuen Konzepten

Wenn du zum ersten Mal auf ein Konzept stößt, das du noch nie gesehen hast:

1. Öffne eine Karte
2. Drücke "Lösung anzeigen" (erscheint nach dem Aufdecken)
3. Lese das vollständige Schritt-für-Schritt-Beispiel (generiert mit Opus — dem stärksten Modell)
4. Erkläre dir selbst, warum jeder Schritt so gemacht wird

Erst nach dem Worked Example aktiv üben — das entspricht dem Cognitive-Load-Prinzip von Sweller.

### Schritt 6: Proof Checker für mathematische Beweise (`/proof/[cardId]`)

Für Karten mit `proof_mode` aktiviert:

1. Schreibe deinen Beweis in natürlicher Sprache ins Textfeld
2. LLM prüft: korrekt, Lücken, nächster Hint
3. Bis zu 5 Versuche mit akkumuliertem Feedback
4. Erst wenn der Beweis korrekt ist, wird die Karte geschlossen

### Schritt 7: Refinement-Queue beobachten (`/refinement`)

Wenn du für ein Konzept 3× "Again" innerhalb von 14 Tagen wählst, schlägt das System automatisch neue Karten aus anderen Perspektiven vor:

- **Geometrische Intuition** — visueller Zugang
- **Anwendungsbeispiel** — konkreter Use-Case
- **Gegenbeispiel** — was das Konzept *nicht* ist
- **Konzeptverbindung** — Relation zu verwandtem Stoff

Du kannst jeden Vorschlag vor dem Approve bearbeiten. Nur approved Karten gehen ins FSRS-System.

### Concept Graph (`/courses/[courseId]/graph`)

Visualisierung aller Konzepte und ihrer Abhängigkeiten. Knoten mit vielen "Again"-Ratings werden als Refinement-Kandidaten markiert — gut für den Überblick welche Bereiche noch unsicher sind.

---

## Empfohlener Wochenrhythmus

| Tag | Was tun |
|---|---|
| **Täglich** | Plan generieren → Review → ggf. 1–2 Coaching-Sessions |
| **Wöchentlich** | Refinement-Queue leeren, Concept-Graph checken |
| **Vor Klausur** | Intensivierung: mehr Reviews pro Tag, mehr Coaching |

**Der wichtigste Hebel:** Kontinuität. 45 Minuten täglich über 12 Wochen schlägt 8-Stunden-Sessions in der letzten Woche — das ist die Kernaussage von Donoghue & Hattie (2021).

---

## Teststatus

```bash
# Backend (158 Tests)
cd backend && uv run pytest -m "not live" -q

# Frontend (49 Tests)
cd frontend && npm test

# Typen & Linting
cd backend && uv run mypy app/ --strict  # 0 errors
cd backend && uv run ruff check app/     # 0 violations
cd frontend && npm run build             # ✅
```

---

## Projektstruktur

```
StudyAssistant/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI-Router
│   │   ├── db/models/    # SQLAlchemy-Modelle (10 Tabellen)
│   │   └── services/     # LLM Gateway, FSRS, RAG, Ingest, Plan Engine
│   ├── alembic/versions/ # 7 Migrationen
│   └── tests/            # 23 Testdateien
├── frontend/
│   ├── app/              # Next.js App Router (8 Routen)
│   └── components/       # 13 React-Komponenten
├── data/                 # SQLite + ChromaDB + PDFs (gitignored)
├── research/             # Lernwissenschaftliche Grundlagen
└── specs/                # Feature-Specs
```

---

## API-Übersicht

```
GET    /health
GET    /me · /me/preferences · PATCH /me/preferences

POST   /api/courses · GET /api/courses · GET /api/courses/{id}
POST   /api/courses/{id}/materials    # PDF-Upload
POST   /api/materials/{id}/ingest     # Ingest-Pipeline

GET    /api/courses/{id}/concepts · GET /api/concepts/{id}/refinement-status
POST   /api/concepts/{id}/refinements

GET    /api/cards · POST /api/cards
POST   /api/cards/{id}/review
POST   /api/cards/{id}/worked-example
POST   /api/cards/{id}/proof-check

GET    /api/review/due · POST /api/reviews/multi

POST   /api/coaching                  # SSE-Stream

GET    /api/analytics/summary · /daily · /monthly

POST   /api/courses/{id}/plan/today
GET    /api/courses/{id}/plan/today
PATCH  /api/plans/{id}/items/{idx}/complete

GET    /api/refinements
PATCH  /api/refinements/{id}/cards/{idx}/approve
PATCH  /api/refinements/{id}/cards/{idx}/reject
```

---

## Quellen

- Dunlosky, J. et al. (2013). Improving Students' Learning With Effective Learning Techniques. *Psychological Science in the Public Interest.*
- Rowland, C. A. (2014). The effect of testing versus restudy on retention. *Psychological Bulletin.*
- Adesope, O. O. et al. (2017). Rethinking the use of tests: A meta-analysis of practice testing. *Review of Educational Research.*
- Donoghue, G. M., & Hattie, J. A. C. (2021). A meta-analysis of ten learning techniques.
- Bjork, E. L., & Bjork, R. A. (2011). Making things hard on yourself, but in a good way. *Psychology and the Real World.*
- Sweller, J., van Merrienboer, J., & Paas, F. (1998). Cognitive architecture and instructional design.
- Mayer, R. E. (2009). *Multimedia Learning* (2nd ed.). Cambridge University Press.
