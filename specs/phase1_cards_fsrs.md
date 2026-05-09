# Spec: Karten-CRUD + FSRS-Scheduler

> Status: `draft`
> Phase: 1
> Verwandte Research: [research/01_learning_science.md](../research/01_learning_science.md) §FSRS, [research/04_system_architecture.md](../research/04_system_architecture.md) §Datenmodell, [research/06_implementation_roadmap.md](../research/06_implementation_roadmap.md) §Phase-1

## Ziel
User legt Karteikarten **manuell** an (kein Auto-Generate), bearbeitet, archiviert und reviewed sie. Reviews triggern den FSRS-Scheduler (`py-fsrs`), der `fsrs_state` aktualisiert und das nächste `due`-Datum setzt. Eine Endpoint-Route gibt alle heute fälligen Karten eines Course zurück (sortiert nach `due` aufsteigend). Ein vollständiger Review-Lauf von 14 Tagen über 100 Karten reproduziert die FSRS-Übergänge deterministisch (Test).

## Nicht-Ziel
- Keine LLM-Karten-Generierung (Phase 2).
- Keine Self-Critique, kein Dedup gegen existierende Karten (Phase 2).
- Keine Card-Embeddings (Phase 2).
- Keine Card-Image-Anhänge.
- Kein FSRS-Optimizer-Run (Default-Parameter aus 700M-Korpus reichen <500 Reviews — siehe research/06 Risiken).
- Keine Tags/Decks neben `course_id`.
- Keine Bulk-Import (CSV o. ä.).

## Akzeptanzkriterien
- [ ] `POST /api/courses/{course_id}/cards` legt eine Karte an. Body: `{type, front, back, bloom_level?, concept_id?}`. `type` ∈ `{basic, cloze, concept_diagram, derivation, proof_skeleton}`. Response `201` mit voller Karte inkl. initialem `fsrs_state` (siehe unten).
- [ ] `GET /api/cards/{id}`, `PATCH /api/cards/{id}`, `DELETE /api/cards/{id}` (DELETE setzt `archived=True`, hard-delete nicht).
- [ ] `GET /api/courses/{course_id}/cards?include_archived=false` listet Karten.
- [ ] `GET /api/courses/{course_id}/cards/due?on=YYYY-MM-DD` liefert alle Karten mit `fsrs_state.due <= on`, sortiert nach `due` aufsteigend, exklusive `archived=True`. Default `on = heute (UTC)`.
- [ ] `POST /api/cards/{id}/review` Body `{rating: 1|2|3|4, reviewed_at?: ISO8601}`. Verhalten:
  - Rating-Mapping: `1=Again, 2=Hard, 3=Good, 4=Easy` (FSRS-Ratings).
  - Wenn `reviewed_at` fehlt: jetzt (UTC).
  - Lädt aktuellen `fsrs_state`, ruft `py-fsrs` Scheduler, schreibt:
    - Neue `reviews`-Row (`card_id`, `reviewed_at`, `rating`, `elapsed_days`, `state_before`, `state_after`).
    - Aktualisiert `cards.fsrs_state`, `cards.review_count++`, bei `rating==1` zusätzlich `cards.lapse_count++`.
  - Response `200 {card_id, fsrs_state, next_due, lapse_count, review_count}`.
- [ ] **Initial-State** bei Karten-Anlegen: `fsrs_state = {stability: 0, difficulty: 0, last_review: null, due: <created_at>, state: "new", reps: 0, lapses: 0}`. Erste Review schiebt `due` korrekt nach FSRS.
- [ ] **Zeitstempel deterministisch:** wenn `reviewed_at` mitgegeben → genau dieser Wert für `elapsed_days` (= `(reviewed_at - last_review).days`, default 0 für erste Review).
- [ ] FSRS-Parameter aus `py-fsrs` Default; **keine eigenen Heuristiken** (CLAUDE.md No-Go).
- [ ] **Determinismus-Test:** 100 Karten, fixierte Rating-Sequenz über 14 Tage, abgeglichen gegen einen committeten JSON-Snapshot der Endzustände.
- [ ] Strukturiertes Logging pro Review: `card_id`, `rating`, `elapsed_days`, `stability_before`, `stability_after`, `due_after`.

## Datenmodell-Änderungen
Tabellen `cards` und `reviews` aus Phase 0 vorhanden. Anpassungen:

- `cards.created_at` und `reviews.reviewed_at` aktuell `TEXT` — auf echtes `DateTime` umstellen, default `datetime.utcnow` (gleiche Begründung wie 1.1). Migration `0003_cards_reviews_datetime.py`.
- `cards.fsrs_state`: bleibt JSON. Schema dokumentiert in Code (Pydantic-Model `FSRSState`).
- Index auf `(course_id, archived, fsrs_state)` ist nicht trivial machbar (JSON-Spalte) → wir indizieren auf `(course_id, archived)` und filtern `due` in Python. Reicht für 1000 Karten/Course.

```sql
CREATE INDEX ix_cards_course_archived ON cards(course_id, archived);
CREATE INDEX ix_reviews_card_id ON reviews(card_id);
```

## API-Änderungen

```
POST /api/courses/{course_id}/cards
Body: {type, front, back, bloom_level?, concept_id?}
Response: 201 {id, course_id, concept_id, type, front, back, bloom_level, fsrs_state, review_count, lapse_count, created_at, archived}

GET /api/cards/{id}
Response: 200 {...} | 404

PATCH /api/cards/{id}
Body: {front?, back?, type?, bloom_level?, concept_id?, archived?}
Response: 200 {...}

DELETE /api/cards/{id}
Response: 204 (soft delete: archived=True)

GET /api/courses/{course_id}/cards?include_archived=false
Response: 200 [{...}, ...]

GET /api/courses/{course_id}/cards/due?on=YYYY-MM-DD
Response: 200 [{...}, ...]   (sortiert nach due asc)

POST /api/cards/{id}/review
Body: {rating: 1|2|3|4, reviewed_at?: ISO8601}
Response: 200 {card_id, fsrs_state, next_due, lapse_count, review_count}
```

Pydantic-Schemas in `backend/app/api/schemas/cards.py`. `FSRSState`-Pydantic-Model spiegelt das `py-fsrs`-State.

## UI-Änderungen
Keine in dieser Spec — Backend-Service. Review-UI in Spec 1.4.

## LLM-Calls
Keine.

## Bibliotheken / Dependencies (neu)
- `py-fsrs` (Pin auf aktuelle Stable-Version) in `pyproject.toml` Hauptdependencies.

## Tests
- Unit (`tests/test_cards_api.py`):
  - POST + GET + PATCH + DELETE Roundtrip.
  - Validierung: ungültiger `type` → 422.
  - PATCH mit `archived=True` → soft delete.
- Unit (`tests/test_fsrs_review.py`):
  - Karte anlegen, ein Review mit `rating=3`, `due` ist >= 1 Tag in der Zukunft, `state` ändert sich von `new` zu `review/learning` (je nach `py-fsrs`).
  - `rating=1` (Again): `lapse_count` +1, `due` wieder kurzfristig.
  - `elapsed_days` korrekt aus `reviewed_at - last_review`.
- Determinismus (`tests/test_fsrs_determinism.py`):
  - Fixture: 100 Karten + Rating-Stream (committet als CSV `tests/fixtures/review_stream_14d.csv`) → durchspielen → final-States gegen `tests/fixtures/expected_states.json` vergleichen. Bei Drift: Test bricht und User entscheidet (Library-Update vs. Snapshot-Refresh).
- Integration (`tests/test_due_query.py`):
  - 5 Karten, manipulierte `due`-Werte (manuell in fsrs_state geschrieben), `GET .../due?on=2026-05-10` liefert nur die fälligen, korrekt sortiert, ohne archivierte.

## Offene Fragen
- `py-fsrs` API-Stabilität: aktuelles Major-Version pinnen, Deprecation-Warnings ggf. fixen. Bei Library-Update den Determinismus-Test als Canary nutzen.
- `concept_id` ist optional; in Phase 1 (kein Auto-Generate) bleibt es meist `null`. In Phase 2 mit Auto-Generation wird's Pflicht für generierte Karten.
- Soll Cloze-Rendering (z. B. `{{c1::Antwort}}`) im Backend geparst werden? — Nein, Frontend rendert. Backend speichert nur den String.
- Time-Zone-Strategie: Alles UTC, Frontend zeigt lokal. Server-`due` ist UTC-Datetime. „Heute fällig" = `due <= 23:59:59 UTC` des angefragten Datums. Edge-Cases bei Zeitzonen-Wechsel akzeptiert für Single-User in Tübingen (CET/CEST).
