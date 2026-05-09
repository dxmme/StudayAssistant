---
description: PRD → parallelisierbare Kanban-Issues als Markdown-Dateien in .claude/issues/
---

# /write-issues <prd-name>

Überführe das PRD `.claude/prds/<prd-name>.md` in priorisierte, abhängigkeitsbewusste Issues.

## Vorgehen

1. Lies `.claude/prds/<prd-name>.md` vollständig.
2. Lies `.claude/GLOSSARY.md` für korrekte Domänen-Bezeichnungen.
3. Erstelle Issues in `.claude/issues/` — **Vertical Slices**, nicht horizontal:

```
✅ Richtig (Vertical Slice):
   issue_01_material_upload_endpoint.md
   → Migration + Service + Endpoint + Test für Upload-Feature

❌ Falsch (Horizontal):
   issue_01_all_migrations.md
   issue_02_all_services.md
   issue_03_all_endpoints.md
```

4. Priorisierung:
   1. Infrastructure (Migrations, Configs)
   2. Tracer Bullets (erster vertikaler Schnitt — minimal funktionierend)
   3. Core Features (Hauptfunktionalität)
   4. Polish (Edge Cases, Error States)

5. Issue-Datei-Format:

```markdown
# Issue <Nr>: <Titel>

**Priorität:** infrastructure | tracer-bullet | feature | polish
**Status:** open | in-progress | done
**Abhängigkeiten:** [Issue-Nr | keine]
**Schätzung:** <S | M | L>

## Ziel
[Ein Satz was dieser Issue erreicht]

## Akzeptanzkriterien
- [ ] [Testbares Kriterium]
- [ ] Tests grün: `pytest tests/test_<name>.py` / `npm test`
- [ ] Type-Check grün: `mypy app/ --strict` / `npm run build`

## Tasks
- [ ] [Konkreter Task 1]
- [ ] [Konkreter Task 2]

## Out of Scope
- [Was explizit nicht in diesem Issue]

## Hinweise
[Pitfalls, kritische Patterns aus GLOSSARY.md, Links zu Research-Docs]
```

6. Erstelle zum Abschluss eine `README.md` in `.claude/issues/` mit:
   - DAG (Abhängigkeits-Graph als ASCII)
   - Welche Issues parallel bearbeitbar sind

**Human Review erforderlich:** Kanban-Plan immer reviewen bevor mit Implementierung begonnen wird.
