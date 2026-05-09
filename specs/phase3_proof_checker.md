# Spec: Proof Checker — Beweis-Reconstruction (Phase 3.2)

> Status: `draft`
> Phase: 3
> Verwandte Research: [research/06_implementation_roadmap.md](../research/06_implementation_roadmap.md) · [research/01_learning_science.md](../research/01_learning_science.md)

## Ziel

Der User öffnet für eine Karte (mit Beweisaufgabe) den Proof-Checker-Modus: er schreibt einen Beweis-Entwurf in Markdown+LaTeX, das LLM prüft schrittweise, gibt strukturiertes Feedback, und nach maximal 5 Turns bewertet das System mit Partial Credit → automatisches FSRS-Rating.

## Nicht-Ziel

- Kein LaTeX-Syntax-Validator (nur inhaltliche Prüfung durch LLM)
- Kein "Whiteboard"-Modus / Handschrift-Input
- Kein Streaming des Checker-Feedbacks (ganzer Block auf einmal)
- Kein Coding-Sandbox-Modus (Phase 4)
- Kein Quiz-Engine-Modus (Phase 4)
- Kein Multi-User-Proof-Review (single user)
- Keine automatische Karten-Rating-Aktualisierung ohne expliziten Abschluss der Session

## Akzeptanzkriterien

- [ ] Karte mit `proof_mode: true` zeigt in der ReviewSession Button "Beweis rekonstruieren"
- [ ] Klick öffnet `/proof/{card_id}` (separate Route, kein Modal)
- [ ] User kann Beweis als Markdown+LaTeX tippen und absenden
- [ ] LLM-Feedback folgt dem Format: "Korrekt bis Schritt N. Fehler: [Beschreibung]. Hinweis: [Sokrates-Frage]" — oder "Vollständig korrekt!"
- [ ] User kann nach Hint erneut einreichen (max 5 Turns insgesamt)
- [ ] Nach 5 Turns ohne korrekten Beweis: Session endet, Partial-Credit-Scoring, Musterantwort angezeigt
- [ ] Partial Credit: korrekte Schritte / Gesamt-Schritte → FSRS-Rating automatisch gesetzt (siehe Scoring-Tabelle)
- [ ] Vollständig korrekter Beweis vor Turn 5 → sofortiger Abschluss, Rating 4
- [ ] `ProofAttempt` wird in DB gespeichert (Turn-Transcript + Final-Rating)
- [ ] `PATCH /api/cards/{card_id}/proof-rating` triggert FSRS-Update (analog zu Review-Rating)
- [ ] `pytest -m "not live"` grün, `npm test` + `npm run build` grün

## Datenmodell-Änderungen

### Neue Spalte `Card.proof_mode`

```sql
-- Migration 0003_proof_mode (render_as_batch=True)
ALTER TABLE cards ADD COLUMN proof_mode BOOLEAN NOT NULL DEFAULT FALSE;
```

```python
# models/cards.py
proof_mode: Mapped[bool] = mapped_column(Boolean, default=False)
```

### Neue Tabelle `proof_attempts`

```sql
CREATE TABLE proof_attempts (
    id           TEXT PRIMARY KEY,
    card_id      TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    turns        JSON NOT NULL,    -- list[ProofTurn] — siehe Format unten
    final_rating INTEGER,          -- 1-4, NULL wenn abgebrochen
    credit_score REAL,             -- 0.0-1.0, Anteil korrekter Schritte
    started_at   TEXT NOT NULL,
    finished_at  TEXT
);
```

```python
# models/proof_attempts.py
class ProofAttempt(Base):
    __tablename__ = "proof_attempts"
    id:           Mapped[str]       = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    card_id:      Mapped[str]       = mapped_column(String(36), ForeignKey("cards.id", ondelete="CASCADE"))
    turns:        Mapped[list]      = mapped_column(JSON, nullable=False, default=list)
    final_rating: Mapped[int|None]  = mapped_column(Integer, nullable=True)
    credit_score: Mapped[float|None]= mapped_column(Float, nullable=True)
    started_at:   Mapped[str]       = mapped_column(String, nullable=False)
    finished_at:  Mapped[str|None]  = mapped_column(String, nullable=True)
```

### Turn-Format (JSON-Schema der `turns`-Spalte)

```json
[
  {
    "turn_number": 1,
    "user_proof": "Sei $n \\in \\mathbb{N}$. Dann...",
    "llm_feedback": "Korrekt bis Schritt 2. Fehler: Du hast die Symmetrie-Annahme nicht begründet. Hinweis: Welche Eigenschaft der Relation erlaubt diesen Schritt?",
    "steps_correct": 2,
    "steps_total": 4,
    "is_correct": false
  }
]
```

## Scoring-Tabelle (Partial Credit → FSRS-Rating)

| Credit Score | FSRS-Rating | Bedeutung |
|---|---|---|
| 1.0 (alle Schritte korrekt, ≤ Turn 3) | 4 — Easy | Problemlos gelöst |
| 1.0 (alle Schritte korrekt, Turn 4-5) | 3 — Good | Mit Aufwand gelöst |
| 0.5–0.99 (> Hälfte korrekt, nicht vollständig) | 2 — Hard | Teilweise korrekt |
| < 0.5 (weniger als Hälfte korrekt, oder alle 5 Turns verbraucht) | 1 — Again | Nicht bestanden |

Der Credit Score = `steps_correct_final / steps_total_final` aus dem letzten Turn.

## API-Änderungen

### `POST /api/cards/{card_id}/proof-attempts`

Startet eine neue ProofAttempt-Session.

```
POST /api/cards/{card_id}/proof-attempts

Response 201:
{
  "id": "uuid",
  "card_id": "uuid",
  "turns": [],
  "final_rating": null,
  "credit_score": null,
  "started_at": "2026-05-09T10:00:00"
}

Response 404: { "detail": "Card not found" }
Response 400: { "detail": "Card is not in proof_mode" }
```

### `POST /api/proof-attempts/{attempt_id}/turns`

Reicht einen Beweis-Entwurf ein, erhält LLM-Feedback.

```
POST /api/proof-attempts/{attempt_id}/turns
Request:
{
  "user_proof": "Sei n ∈ ℕ..."
}

Response 200 (noch nicht korrekt, Turns < 5):
{
  "turn": {
    "turn_number": 1,
    "user_proof": "...",
    "llm_feedback": "Korrekt bis Schritt 2. Fehler: ... Hinweis: ...",
    "steps_correct": 2,
    "steps_total": 4,
    "is_correct": false
  },
  "turns_remaining": 4,
  "is_finished": false,
  "final_rating": null
}

Response 200 (korrekt ODER 5 Turns verbraucht, is_finished: true):
{
  "turn": { ... },
  "turns_remaining": 0,
  "is_finished": true,
  "final_rating": 3,
  "credit_score": 0.85,
  "reference_answer": "<card.answer — nur bei is_finished: true gezeigt>"
}

Response 404: { "detail": "Attempt not found" }
Response 409: { "detail": "Attempt already finished" }
```

**LLM-Call-Logik:**
1. Lade `ProofAttempt` + `Card` + Turn-History
2. System-Block (gecacht):
   ```
   Du bist ein strenger aber fairer Mathematik-Tutor.
   Aufgabe: {card.question}
   Referenz-Lösung (NICHT direkt zeigen): {card.answer}

   Analysiere den Beweis-Entwurf des Users schrittweise.
   Antworte NUR in diesem Format:
   - Falls korrekt: "Vollständig korrekt! [kurze Bestätigung]"
   - Falls fehlerhaft: "Korrekt bis Schritt N. Fehler: [präzise Beschreibung]. Hinweis: [Sokrates-Frage]"
   Gib außerdem an: STEPS_CORRECT: X, STEPS_TOTAL: Y
   ```
3. Messages: alle bisherigen Turns als Kontext + neue User-Message
4. `LLMGateway.complete(system_block, messages, tier="hard")`
5. Parse `STEPS_CORRECT: X, STEPS_TOTAL: Y` aus Response
6. Berechne ob korrekt, updaten Turn-Array, persistieren
7. Falls korrekt oder Turn 5 erreicht: `finished_at` setzen, `final_rating` + `credit_score` berechnen

### `PATCH /api/proof-attempts/{attempt_id}/apply-rating`

Überträgt das `final_rating` auf die FSRS-State der Karte (triggert FSRS-Update wie ein normales Review).

```
PATCH /api/proof-attempts/{attempt_id}/apply-rating

Response 200:
{
  "card_id": "uuid",
  "applied_rating": 3,
  "new_fsrs_state": { "stability": ..., "difficulty": ..., "due": "..." }
}

Response 404: { "detail": "Attempt not found" }
Response 400: { "detail": "Attempt not finished yet" }
```

**Neue Dateien (Backend):**
- `backend/app/api/proof_checker.py` — Router (`/api/cards` + `/api/proof-attempts`)
- `backend/app/api/schemas/proof_checker.py` — Pydantic-Schemas
- `backend/alembic/versions/XXXX_proof_attempt.py` — Migration (proof_mode + proof_attempts)

## UI-Änderungen

### Änderung in `ReviewSession.tsx`

Falls `card.proof_mode === true` und Antwort aufgedeckt: Link-Button "Beweis rekonstruieren" → navigiert zu `/proof/{card_id}`.

### Neue Route `app/proof/[cardId]/page.tsx`

Server Component — lädt Card, startet Attempt via `POST /api/cards/{cardId}/proof-attempts`.

### Neue Komponente `ProofCheckerSession.tsx`

Client Component.

```
┌──────────────────────────────────────────────────────────────┐
│  Beweis-Rekonstruktion                     Turn 2 / 5        │
│  ────────────────────────────────────────────────────────    │
│  Aufgabe: Zeige, dass die VC-Dim. des Halbraums in ℝᵈ = d+1  │
│                                                              │
│  Dein Beweis:                                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Sei S = {e₁,...,e_{d+1}} ⊂ ℝᵈ...                   │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│  [ Einreichen ]                                              │
│                                                              │
│  Feedback (Turn 1):                                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Korrekt bis Schritt 2. Fehler: Die Unabhängigkeit    │   │
│  │ der Vektoren wurde nicht gezeigt.                    │   │
│  │ Hinweis: Welche Eigenschaft garantiert lineare       │   │
│  │ Unabhängigkeit bei Standardbasisvektoren?            │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘

--- Nach Abschluss (is_finished: true) ---

┌──────────────────────────────────────────────────────────────┐
│  Ergebnis: 85% korrekt → Rating: Hard (2)                    │
│  ────────────────────────────────────────────────────────    │
│  Musterantwort:                                              │
│  [card.answer in MarkdownMath gerendert]                     │
│                                                              │
│  [ Rating auf Karte übertragen ]  [ Zurück zur Review ]      │
└──────────────────────────────────────────────────────────────┘
```

- Textarea für Markdown+LaTeX-Eingabe (monospace-Font)
- KaTeX-Preview unterhalb der Textarea (Live-Render via `MarkdownMath`)
- Turn-History scrollbar, älteste oben
- Button disabled während Laden
- "Rating auf Karte übertragen" → `PATCH apply-rating` → zurück zu `/review`

## LLM-Calls

| Eigenschaft | Wert |
|---|---|
| Tier | `hard` (claude-opus-4-7) |
| Prompt-Caching | System-Block mit Aufgabe + Referenzlösung gecacht (ephemeral) |
| Turn-Context | Alle bisherigen Turns als Messages (Multi-Turn) |
| Erwartete Input-Tokens | ~1000–2500 (wächst mit Turns) |
| Erwartete Output-Tokens | ~200–400 pro Turn |
| Streaming | Nein |

## Tests

### Backend (`backend/tests/test_proof_checker.py`)

- `test_create_attempt` — POST für Card mit `proof_mode=True` → 201, leere `turns`
- `test_create_attempt_non_proof_card` — POST für normale Card → 400
- `test_create_attempt_card_not_found` — unbekannte Card → 404
- `test_submit_turn_feedback` — Mock LLM → Turn-Objekt im Response, `turns_remaining` korrekt
- `test_submit_turn_correct_proof` — Mock LLM mit "Vollständig korrekt!" → `is_finished: true`, `final_rating: 4`
- `test_submit_turn_max_turns_exceeded` — 5 Turns gesendet → 6. Turn → 409
- `test_submit_turn_parse_steps` — LLM gibt `STEPS_CORRECT: 3, STEPS_TOTAL: 4` → `credit_score ≈ 0.75` → Rating 2
- `test_partial_credit_scoring` — verschiedene Credit-Scores → korrekte Rating-Zuordnung (Tabelle)
- `test_apply_rating_updates_fsrs` — PATCH → FSRS-State der Card aktualisiert (wie Review)
- `test_apply_rating_not_finished` — PATCH vor Abschluss → 400
- `test_attempt_history_persisted` — Turn-Array in DB nach jedem Submit aktualisiert

### Frontend (`frontend/tests/proof-checker.test.tsx`)

- `test_renders_task_and_textarea` — Aufgabe sichtbar, Textarea vorhanden
- `test_submit_calls_api` — Klick "Einreichen" → fetch mit POST aufgerufen
- `test_feedback_rendered_in_markdown` — gemocktes Feedback → `MarkdownMath` gerendert
- `test_turn_counter_updates` — nach Submit: "Turn 2 / 5" sichtbar
- `test_finished_state_shows_reference` — `is_finished: true` → Musterantwort sichtbar
- `test_apply_rating_button_calls_patch` — Klick → PATCH aufgerufen

## Offene Fragen

- LLM-Response-Parsing von `STEPS_CORRECT` / `STEPS_TOTAL`: Falls LLM das Format nicht einhält, Fallback `steps_correct=0` → Rating 1. Alternativ: separaten strukturierten Output-Block via JSON-Extraktion.
- Soll der User den Proof-Checker auch ohne vorherige ReviewSession öffnen (z. B. direkt über Card-Detail)? → Annahme: Ja, direkt via `/proof/{card_id}` erreichbar.
- `proof_mode` per Card manuell setzen (PATCH /api/cards/{id} mit `{ "proof_mode": true }`)? → Ja, bestehender PATCH-Endpoint bekommt `proof_mode` als optionales Feld.
