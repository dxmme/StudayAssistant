---
description: Grill-Session → strukturiertes PRD-Dokument in .claude/prds/
---

# /write-a-prd <name>

Überführe die aktuelle Grill-Session (oder Konversation) in ein PRD unter `.claude/prds/<name>.md`.

## Vorgehen

1. Lies die bisherige Konversation und extrahiere alle Entscheidungen.
2. Konsultiere `.claude/GLOSSARY.md` — nutze nur kanonische Domänen-Begriffe.
3. Schreibe `.claude/prds/<name>.md`:

```markdown
# PRD: <Name>

**Phase:** <Phase-Nr>
**Status:** draft | review | approved
**Datum:** <YYYY-MM-DD>
**Abhängigkeiten:** <andere Specs/PRDs>

---

## Problem Statement
[Was ist das Problem / die Anforderung? Warum jetzt?]

## Lösung
[Wie lösen wir es? Auf Domänen-Ebene, nicht Implementierungsebene]

## Akzeptanzkriterien
- [ ] [Testbares Kriterium 1]
- [ ] [Testbares Kriterium 2]
- [ ] ...

## Datenmodell-Auswirkungen
- Neue Tabellen: [keine | Name + Felder]
- Geänderte Tabellen: [keine | Tabelle + Delta]
- Neue Alembic-Migration: [keine | 000X_<name>.py]

## API-Surface
| Method | Path | Request | Response |
|---|---|---|---|
| POST | /api/... | {...} | {...} |

## Proposed Module-Changes
- `backend/app/...` — [was ändert sich]
- `frontend/app/...` — [was ändert sich]

## LLM-Involvement
- Tier: [default | cheap | hard | keiner]
- Prompt Caching: [ja (RAG-Kontext) | nein]
- Streaming: [ja (SSE) | nein]

## Test-Strategie
- Backend Unit-Tests: [pytest, welche Szenarien]
- Frontend Tests: [vitest, welche Komponenten]
- Live-Tests: [ja @pytest.mark.live | nein]
- E2E: [Playwright | nein]

## Out of Scope
- [Explizit was NICHT gemacht wird]
- [Phase-1-Ausschlüsse die nicht versehentlich eingebaut werden]
```

4. Markiere Status als `draft`.
5. Liste offene Fragen am Ende.

**Warnung:** PRD ist nicht der Code. Veraltete PRDs aus `.claude/prds/` löschen sobald nicht mehr relevant (Doc Rot).
