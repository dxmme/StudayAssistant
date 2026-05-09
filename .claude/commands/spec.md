---
description: Erzeuge eine neue Spec aus dem Template
---

# /spec <name>

Erzeuge eine neue Spec-Datei in `specs/<name>.md` auf Basis von [specs/TEMPLATE.md](../../specs/TEMPLATE.md).

Vorgehen:
1. Lies `specs/TEMPLATE.md`.
2. Frage den User nach: Ziel des Features, Phase, Akzeptanzkriterien (falls nicht aus dem Argument klar).
3. Konsultiere die relevanten Research-Docs (`research/04_*.md` für Architektur, `research/05_*.md` für UI).
4. Schreibe `specs/<name>.md` aus, lasse keine Platzhalter `<...>` stehen.
5. Markiere Status als `draft` und liste am Ende offene Fragen.

**Nicht** sofort implementieren. Spec → User-Review → erst dann Code.
