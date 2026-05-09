# Spec: Material-Upload + PDF-Parsing

> Status: `draft`
> Phase: 1
> Verwandte Research: [research/04_system_architecture.md](../research/04_system_architecture.md) §A, [research/06_implementation_roadmap.md](../research/06_implementation_roadmap.md) §Phase-1

## Ziel
Ein User kann ein PDF (Foliensatz, Skript, Altklausur) zu einem Course hochladen. Datei landet auf der Platte unter `data/uploads/<course_id>/<material_id>.pdf`. `marker-pdf` konvertiert das PDF Math-aware nach Markdown+LaTeX und schreibt das Resultat als Sidecar-Datei. `materials`-Row wird angelegt mit `indexed=False`. Kein Embedding, keine Konzept-Extraktion (kommt in 1.2).

## Nicht-Ziel
- Kein Chunking, kein Embedding, kein Vector-Store (→ Spec 1.2).
- Keine Konzept-Extraktion (→ Spec 1.2).
- Keine Frontend-UI für den Upload (→ Spec 1.4 / Phase 2 — für Phase 1 reicht `curl` / API-Test).
- Keine Multi-File-Uploads, kein Drag-and-Drop.
- Keine Virenscanner, keine Größen-Quotas (single-user, lokal).
- Kein Auto-Retry bei Parse-Fehler — User sieht Fehler und lädt neu hoch.

## Akzeptanzkriterien
- [ ] `POST /api/courses` erstellt einen Course (Body: `{name, semester?, exam_date?, exam_format?, professor?, notes?}`), Response `201 {id, ...}`.
- [ ] `GET /api/courses` listet alle Courses, `GET /api/courses/{id}` gibt einen einzelnen zurück (404 wenn nicht existent).
- [ ] `POST /api/courses/{course_id}/materials` akzeptiert `multipart/form-data` mit:
  - `file`: PDF (Pflicht, Content-Type `application/pdf`)
  - `type`: `lecture_slides | script | past_exam | topic_overview` (Pflicht)
  - `title`: optional, default = Original-Filename ohne Extension
- [ ] Datei wird gespeichert unter `data/uploads/{course_id}/{material_id}.pdf` (UUID4 für `material_id`). Verzeichnis wird auto-angelegt.
- [ ] Nach Upload startet **synchron** der Parse-Schritt:
  - `marker-pdf` (Library, kein Subprocess) konvertiert PDF → Markdown.
  - Output wird gespeichert als `data/uploads/{course_id}/{material_id}.md`.
  - `materials.page_count` wird aus `marker-pdf` befüllt.
- [ ] Bei Parse-Fehler: Datei + Row werden gelöscht, Response `422 {error: "parse_failed", detail: "..."}`.
- [ ] Bei Erfolg: Response `201 {id, course_id, type, title, file_path, page_count, indexed: false, uploaded_at}`.
- [ ] `GET /api/courses/{course_id}/materials` listet alle Materialien des Course (mit `indexed`-Flag).
- [ ] `GET /api/materials/{id}/markdown` liefert die geparste Markdown-Datei als `text/markdown`. 404 falls nicht existent.
- [ ] `DELETE /api/materials/{id}` löscht Row + PDF + Markdown vom Filesystem (404 wenn nicht existent, 204 bei Erfolg).
- [ ] Strukturiertes Logging pro Upload: `material_id`, `course_id`, `file_size_bytes`, `page_count`, `parse_duration_ms`.
- [ ] Wenn `marker-pdf` länger als 120s braucht: Logwarnung `slow_parse`, aber kein Hard-Timeout.

## Datenmodell-Änderungen
Tabelle `materials` existiert bereits aus Phase 0. Diese Spec **nutzt** sie nur. Anpassungen:

```sql
-- bereits vorhanden, hier zur Erinnerung:
-- materials(id, course_id, type, title, file_path, page_count, indexed, uploaded_at)
```

Migration nötig: `uploaded_at` ist aktuell `TEXT` (siehe `app/db/models/materials.py:22`). Auf echtes `DateTime(timezone=False)` umstellen, default `datetime.utcnow`. Neue Migration: `0002_materials_uploaded_at_datetime.py`.

## API-Änderungen

```
POST /api/courses
Request:  {name, semester?, exam_date?, exam_format?, professor?, notes?}
Response: 201 {id, name, semester, exam_date, exam_format, professor, notes, created_at}

GET /api/courses
Response: 200 [{id, name, ...}, ...]

GET /api/courses/{id}
Response: 200 {id, name, ...} | 404

POST /api/courses/{course_id}/materials
Content-Type: multipart/form-data
Fields:
  file:  PDF (binary)
  type:  "lecture_slides" | "script" | "past_exam" | "topic_overview"
  title: string (optional)
Response: 201 {id, course_id, type, title, file_path, page_count, indexed, uploaded_at}
          | 404 (course not found)
          | 415 (not application/pdf)
          | 422 {error: "parse_failed", detail}

GET /api/courses/{course_id}/materials
Response: 200 [{id, type, title, page_count, indexed, uploaded_at}, ...]

GET /api/materials/{id}/markdown
Response: 200 (Content-Type: text/markdown) | 404

DELETE /api/materials/{id}
Response: 204 | 404
```

Pydantic-Schemas in `backend/app/api/schemas/courses.py` und `materials.py`.

## UI-Änderungen
Keine in dieser Spec. Frontend-Upload-UI kommt in Phase 2 (oder Hilfs-Form in Phase-1-Coaching-UI 1.5 falls bequem).

## LLM-Calls
Keine.

## Bibliotheken / Dependencies (neu)
- `marker-pdf` — Math-aware PDF→Markdown, ist im research-Doc als Pflicht festgehalten.
- `python-multipart` — schon in `pyproject.toml` vorhanden.

`pyproject.toml`: `marker-pdf` in `[project.optional-dependencies].ingest` ergänzen (zusammen mit `pymupdf` als Fallback).

## Tests
- Unit (`tests/test_courses_api.py`):
  - CRUD für Courses (POST + GET + GET-by-id 404).
- Unit (`tests/test_materials_api.py`):
  - Mock von `marker-pdf` (Module-Level-Stub, der ein bekanntes Markdown zurückgibt).
  - Upload eines kleinen Test-PDF (`tests/fixtures/sample.pdf`, ~2 Seiten, in Repo committet) → 201, Datei existiert auf Disk, Markdown-Sidecar existiert, Row in DB hat `page_count=2`.
  - Upload mit `Content-Type: text/plain` → 415.
  - Upload zu nicht-existentem Course → 404.
  - Mock-`marker-pdf` wirft `RuntimeError` → 422 + Datei + Row aufgeräumt.
  - DELETE entfernt Row und beide Files.
- Integration (`tests/test_materials_parse_live.py`, `@pytest.mark.live_pdf`):
  - Echter `marker-pdf`-Aufruf mit dem Sample-PDF, ohne Mock. Nur ausgeführt mit `pytest -m live_pdf`. Bestätigt, dass die Library tatsächlich integriert ist.

## Offene Fragen
- `marker-pdf` braucht beim Erstaufruf Modell-Downloads (~1-2 GB). Wo dokumentieren? — README-Zeile in `backend/README.md`: „Erster Material-Upload kann mehrere Minuten dauern (Modell-Download)."
- Synchroner Parse blockiert den HTTP-Request bis zu ~30s/Folie. Ist das ok für Phase 1? — Ja, single-user. Async/Background-Jobs (Celery o. ä.) erst falls UX leidet (Phase 2).
- Soll `material_chunks` schon in dieser Spec befüllt werden? — Nein, das ist Spec 1.2. Hier nur Material + Markdown-Sidecar.
- Was ist mit doppelten Uploads (gleiche Datei zweimal)? — Phase 1: erlauben, separate `id`. Dedup ist Nice-to-have für später.
