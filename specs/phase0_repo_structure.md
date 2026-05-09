# Spec: Repo Structure & Tooling

> Status: `draft`
> Phase: 0
> Verwandte Research: [research/06_implementation_roadmap.md](../research/06_implementation_roadmap.md)

## Ziel
Leeres Repo bekommt verbindliche Verzeichnisse, Dependency-Files und `.gitignore`. `uv sync` und `pnpm install` laufen ohne Fehler durch.

## Nicht-Ziel
- Kein Anwendungscode (keine FastAPI-Routes, keine Next-Pages).
- Keine CI-Konfiguration.
- Keine Pre-Commit-Hooks (kommt später, falls nötig).

## Akzeptanzkriterien
- [ ] `backend/pyproject.toml` existiert, deklariert `python = "^3.12"` und gepinnte Dependencies: `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `alembic`, `pydantic`, `pydantic-settings`, `python-multipart`, `anthropic`, `chromadb`, `py-fsrs`, `marker-pdf`, `pymupdf`. Dev-Dependencies: `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `black`, `mypy`.
- [ ] `frontend/package.json` existiert, deklariert gepinnte Dependencies: `next`, `react`, `react-dom`, `typescript`, `tailwindcss`, `postcss`, `autoprefixer`, `katex`, `@tanstack/react-query`, `zustand`. Dev: `vitest`, `@testing-library/react`, `eslint`, `eslint-config-next`.
- [ ] `frontend/tsconfig.json` mit `"strict": true`.
- [ ] `.gitignore` im Root deckt: `data/`, `__pycache__/`, `*.pyc`, `.venv/`, `node_modules/`, `.next/`, `.env`, `.env.local`, `*.db`, `chroma/`.
- [ ] `data/`-Unterordner: `data/sqlite/`, `data/chroma/`, `data/uploads/` (jeweils mit `.gitkeep`).
- [ ] `shared/README.md` Platzhalter („Cross-cutting types — populated in Phase 1").
- [ ] `backend/.env.example` mit `ANTHROPIC_API_KEY=` und `DATABASE_URL=sqlite:///./data/sqlite/study.db`.
- [ ] `uv sync` (im `backend/`) und `pnpm install` (im `frontend/`) laufen exit-code 0.

## Datenmodell-Änderungen
Keine.

## API-Änderungen
Keine.

## UI-Änderungen
Keine.

## LLM-Calls
Keine.

## Tests
- Manuell: `cd backend && uv sync` → exit 0.
- Manuell: `cd frontend && pnpm install` → exit 0.
- Kein Pytest/Vitest in dieser Spec.

## Offene Fragen
- Soll `shared/` ein eigenes `package.json` bekommen (für TS-Codegen aus Pydantic), oder reicht ein Subpfad? — Antwort: erst in Phase 1, wenn Schemas relevant werden.
- `marker-pdf` zieht große Modelle nach. In `pyproject.toml` als optional-Group `[ingest]` oder als Default-Dep? — Default-Dep, weil ohnehin Pflicht.
