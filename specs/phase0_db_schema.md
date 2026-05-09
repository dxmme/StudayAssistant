# Spec: DB-Schema & Alembic-Migration

> Status: `draft`
> Phase: 0
> Verwandte Research: [research/04_system_architecture.md](../research/04_system_architecture.md)

## Ziel
SQLAlchemy-Models existieren für alle in `research/04` definierten Tabellen, Alembic ist initialisiert, eine erste Migration erzeugt das vollständige Schema in `data/sqlite/study.db`.

## Nicht-Ziel
- Keine ORM-Queries / Repositories — nur Tabellen-Definitionen.
- Kein Seed-Data.
- Keine Indizes über das hinaus, was `research/04` explizit nennt.
- Keine Performance-Optimierungen.

## Akzeptanzkriterien
- [ ] `backend/app/db/base.py` enthält `Base = DeclarativeBase`.
- [ ] `backend/app/db/models/` enthält Module pro Aggregat (`courses.py`, `materials.py`, `concepts.py`, `cards.py`, `reviews.py`, `worked_examples.py`, `quiz.py`, `coaching.py`, `plans.py`, `mock_exams.py`).
- [ ] Alle in `research/04_system_architecture.md` definierten Tabellen sind als SQLAlchemy-Models abgebildet (mit Spalten, Typen, FKs aus dem dortigen Schema).
- [ ] `alembic init alembic` ausgeführt, `env.py` referenziert `Base.metadata` aus `app.db.base`.
- [ ] Eine generierte Migration `0001_initial_schema.py` legt alle Tabellen + FK-Constraints an.
- [ ] `alembic upgrade head` läuft fehlerfrei und erzeugt `data/sqlite/study.db` mit allen Tabellen.
- [ ] `alembic downgrade base` droppt alles wieder fehlerfrei.
- [ ] `pytest backend/tests/test_migrations.py` grün: upgrade → introspect-Tabellenliste matcht Erwartung → downgrade.

## Datenmodell-Änderungen
**Vollständig nach [research/04_system_architecture.md](../research/04_system_architecture.md).** Tabellen (Übersicht):

| Tabelle | Zweck |
| --- | --- |
| `courses` | Vorlesung / Modul |
| `materials` | Hochgeladene Dateien (PDF etc.) |
| `material_chunks` | Chunked Inhalte für RAG |
| `concepts` | Extrahierte Konzepte |
| `concept_edges` | Knowledge-Graph-Kanten (Prerequisites) |
| `cards` | Lernkarten (Q+A, mit `fsrs_state`) |
| `reviews` | FSRS-Review-Log pro Karte |
| `worked_examples` | Faded Worked Examples + Stages |
| `quiz_questions` | Quiz-Fragen (per Konzept) |
| `quiz_attempts` | User-Versuche + Bewertung |
| `coaching_sessions` | Sokratische Sessions + Diagnostic |
| `plan_sessions` | Tägliche Session-Pläne |
| `mock_exams` | Klausur-Simulationen + Auswertung |

> **Pflicht:** Spalten exakt wie in `research/04` (inkl. `created_at`, `updated_at`, JSON-Spalten für FSRS-State usw.).

```sql
-- Genaue Statements werden von Alembic generiert und gegen research/04 abgeglichen.
-- Bei Diskrepanz: research/04 ist die Quelle der Wahrheit.
```

## API-Änderungen
Keine.

## UI-Änderungen
Keine.

## LLM-Calls
Keine.

## Tests
- `test_migrations.py` (Integration):
  - Setup: temporäre SQLite-DB.
  - `alembic upgrade head` via Subprocess oder Programmatic API.
  - Mit `sqlalchemy.inspect(engine).get_table_names()` prüfen, dass alle erwarteten Tabellen vorhanden sind.
  - `alembic downgrade base` → keine Tabellen mehr.
- Kein Unit-Test pro Model nötig — Models sind reine Deklarationen.

## Offene Fragen
- JSON-Spalten (z. B. `cards.fsrs_state`): SQLite hat `JSON` als TEXT-Alias. Reicht das, oder strikt validierte Sub-Tabelle? — Reicht TEXT/JSON für Phase 0; Validierung passiert auf Pydantic-Layer.
- `material_chunks` doppelt vorhanden in Vector-Store (Chroma) und SQL? — Ja, SQL hält Metadata + Original-Text, Chroma nur Embeddings + ID-Pointer.
- Sollen FKs `ON DELETE CASCADE` haben? — Standard: ja für Eltern→Kind (z. B. `course → materials → chunks`), nein für Cross-References (z. B. `concept ↔ card`).
