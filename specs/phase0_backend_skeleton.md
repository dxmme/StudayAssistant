# Spec: Backend Skeleton (FastAPI + Auth-Stub)

> Status: `draft`
> Phase: 0
> Verwandte Research: [research/04_system_architecture.md](../research/04_system_architecture.md)

## Ziel
FastAPI-App startet via `uvicorn`, beantwortet `GET /health`, hat Auth-Dependency die einen festen Single-User liefert.

## Nicht-Ziel
- Keine Business-Endpoints (Materials, Cards, Reviews).
- Keine echte Auth (kein OAuth, kein Login-Form). Single-User lokal reicht laut Roadmap-No-Go.
- Keine DB-Anbindung in dieser Spec (kommt in `phase0_db_schema.md`).

## Akzeptanzkriterien
- [ ] `uvicorn app.main:app --reload` startet ohne Fehler auf `:8000`.
- [ ] `GET /health` → `200 {"status": "ok", "version": "0.0.1"}`.
- [ ] `app.core.auth.get_current_user()` ist eine FastAPI-Dependency, die immer `User(id="local", name="local-user")` zurückliefert.
- [ ] `GET /me` (geschützt durch `get_current_user`) → `200 {"id":"local","name":"local-user"}`.
- [ ] CORS-Middleware erlaubt `http://localhost:3000`.
- [ ] Settings via `pydantic-settings` aus `.env` (mind. `ANTHROPIC_API_KEY`, `DATABASE_URL`).
- [ ] Logging konfiguriert: strukturiertes JSON auf stdout (level INFO).
- [ ] `pytest backend/tests/test_health.py` grün.

## Datenmodell-Änderungen
Keine.

## API-Änderungen
```
GET /health
  → 200 { "status": "ok", "version": "0.0.1" }

GET /me
  → 200 { "id": "local", "name": "local-user" }
```

## Verzeichnisstruktur
```
backend/
  app/
    main.py              # FastAPI app, routes inclusion, CORS
    core/
      config.py          # pydantic Settings
      auth.py            # get_current_user dependency
      logging.py         # structured logging setup
    api/
      health.py          # GET /health
      me.py              # GET /me
  tests/
    test_health.py
    test_me.py
  pyproject.toml
  .env.example
```

## UI-Änderungen
Keine.

## LLM-Calls
Keine.

## Tests
- Unit/Integration (`pytest`):
  - `test_health.py`: `httpx.AsyncClient` → GET `/health` → 200 + Body-Schema.
  - `test_me.py`: GET `/me` → 200 + `{"id":"local","name":"local-user"}`.
- Kein e2e in dieser Phase.

## Offene Fragen
- Version-String: hardcoded oder aus `pyproject.toml` lesen? — Hardcoded für Phase 0, später `importlib.metadata`.
- `/me` notwendig, oder reicht der Stub als interne Dependency? — Notwendig: Frontend braucht später einen Endpoint, den es aufrufen kann.
