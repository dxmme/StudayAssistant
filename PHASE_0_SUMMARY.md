# Phase 0 — Foundations Complete

**Status:** ✅ ALL 5 SPECS IMPLEMENTED & TESTED  
**Date:** 2026-05-08  
**Next Phase:** Phase 1 (Material Ingestion)

---

## Quick Recap: Was wurde implementiert?

### Spec 1: DB Schema + Alembic Migration
- 13 SQLAlchemy Models mit Mapped-Syntax
- FK constraints mit CASCADE
- Auto-generated Migration (`0001_initial_schema.py`)
- ✅ Test: Upgrade/Downgrade funktioniert

### Spec 2: FastAPI + Health Endpoints
- CORS configured für localhost:3000
- Settings via Pydantic V2 (`SettingsConfigDict`)
- Structured JSON logging (extra-Felder supported)
- ✅ Test: `/health` Endpoint antwortet

### Spec 3: DB Migrations (part of Spec 1)
- Alembic batch mode für SQLite
- Programmatisches Test-Pattern

### Spec 4: Frontend Skeleton
- Next.js 16 (App Router, TypeScript strict)
- KaTeX rendering für LaTeX-Formeln
- Tailwind v4, React 19
- ✅ Tests: 2/2 bestanden
- ✅ Dev-Server: läuft auf :3000

### Spec 5: LLM Gateway
- `LLMGateway` Service mit Model-Routing (default=Sonnet, cheap=Haiku, hard=Opus)
- **Prompt Caching:** System-Block bekommt `cache_control: ephemeral`
- **Retry-Logic:** 3 Retries bei 529 (overloaded), Exponential Backoff
- Structured Logging: `model`, `tier`, `tokens_in/out`, `cache_read/create`, `latency_ms`
- ✅ Tests: 4 Unit-Tests (kein API-Key) + 1 Live-Test (mit Key)

---

## Running Tests

### Backend
```bash
cd backend

# All unit tests (default)
.venv/bin/python -m pytest tests/ -v --ignore=tests/test_llm_gateway_live.py

# Output: 7/7 PASSED
```

### Frontend
```bash
cd frontend

# Run tests
npm test

# Output: 2/2 PASSED

# Dev server
npm run dev  # → http://localhost:3000
```

---

## Environment Setup (for next session)

```bash
# Backend
cd backend
uv sync --all-extras

# Frontend
cd frontend
npm install

# Start dev server
npm run dev  # Terminal 1
cd ../backend && .venv/bin/python -m uvicorn app.main:app --reload  # Terminal 2
```

---

## Critical Code Patterns

### 1. LLMGateway Usage
```python
from app.services.llm_gateway import LLMGateway, Message

gw = LLMGateway()
result = gw.complete(
    system="You are a tutor...",
    messages=[Message("user", "Explain backpropagation")],
    tier="default",  # or "cheap" (haiku) or "hard" (opus)
    max_tokens=1024,
)

print(f"Tokens used: {result.usage.input_tokens}")
print(f"Cache read: {result.usage.cache_read_input_tokens}")
```

### 2. Logging with Extra Fields
```python
import logging

logger = logging.getLogger(__name__)
logger.info("operation_complete", extra={
    "operation": "extract_concepts",
    "model": "haiku",
    "tokens": 150,
    "latency_ms": 1200,
})
# Output: {"timestamp": "...", "level": "INFO", "operation": "extract_concepts", "model": "haiku", ...}
```

### 3. SQLAlchemy Model (Mapped Syntax)
```python
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, JSON

class Concept(Base):
    __tablename__ = "concepts"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(2000))
```

### 4. React Component with KaTeX
```typescript
import katex from 'katex'

export function Math({ tex }: { tex: string }) {
  const html = katex.renderToString(tex, { throwOnError: false })
  return <div dangerouslySetInnerHTML={{ __html: html }} />
}

// Usage
<Math tex="\\frac{\\partial L}{\\partial w} = -\\eta \\nabla_w L" />
```

---

## Files Changed This Session

### New
- `backend/app/services/llm_models.py`
- `backend/app/services/llm_gateway.py`
- `backend/tests/test_llm_gateway.py`
- `backend/tests/test_llm_gateway_live.py`

### Modified
- `backend/app/core/logging.py` — added extra-field support
- `backend/pyproject.toml` — added pytest live-marker
- `frontend/package.json` — added test-script
- `frontend/app/components/Math.tsx` — removed `'use server'`

### Created in Session (other)
- DB Schema (13 models)
- Alembic setup
- FastAPI skeleton
- Frontend skeleton with KaTeX
- All tests

---

## Next: Phase 1 (Material Ingestion)

Phase 1 starts with **Spec 1.1: Material Upload**:
1. Upload PDF via Frontend
2. Parse PDF (marker-pdf, pymupdf)
3. Extract text
4. Call LLMGateway with `tier="cheap"` (Haiku) to extract concepts
5. Generate cards automatically
6. Store in DB

Key Infrastructure Ready:
- ✅ LLMGateway with caching (can reuse system prompt for multiple documents)
- ✅ Async support (FastAPI)
- ✅ Logging infrastructure
- ✅ DB schema with Material + Concept tables

---

## Debugging Tips

### Backend fails to start?
1. Check `.env` has `ANTHROPIC_API_KEY` and `DATABASE_URL`
2. Run migrations: `cd backend && alembic upgrade head`
3. Check logs: JSON format with `timestamp`, `level`, `message`

### Frontend doesn't render?
1. Check `:3000` in browser
2. `npm run build` should complete without errors
3. KaTeX needs CDN link in layout.tsx (already there)

### Tests fail?
- Backend: `.venv/bin/python -m pytest tests/ -v`
- Frontend: `npm test`
- Live LLM test: `pytest tests/test_llm_gateway_live.py -m live -v` (needs API key)

---

## Important Notes for Next Session

1. **Model Selection:** Sonnet 4.6 recommended for Phase 1 (better for code + complex logic)
2. **Prompt Caching:** Already implemented in LLMGateway — Phase 1 will reuse system prompts across documents (cache hits expected)
3. **Async:** All FastAPI endpoints should be `async def` when calling LLMGateway
4. **Testing:** Unit tests (pytest) run without API key. Live tests marked with `@pytest.mark.live` and skipped by default
5. **Type Safety:** Backend uses mypy strict, Frontend uses TS strict — maintain this

---

For ultra-detailed breakdown, see: `~/.claude/projects/-home-ichzahlalles/memory/PHASE_0_COMPLETE.md`
