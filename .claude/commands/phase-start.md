---
description: Starte eine Phase aus der Roadmap (Skeleton + erste Specs)
---

# /phase-start <n>

Initialisiere Phase `n` aus [research/06_implementation_roadmap.md](../../research/06_implementation_roadmap.md).

Vorgehen:
1. Lies den Phase-`n`-Abschnitt aus der Roadmap.
2. Zeige dem User die Tasks-Liste der Phase und frage: „Bestätigen, dass wir genau diese Phase angehen?"
3. Wenn bestätigt:
   - Lege Verzeichnisstruktur an (siehe CLAUDE.md → Repo-Struktur), nur falls noch nicht vorhanden.
   - Schreibe pro Task aus der Phase eine Spec in `specs/phase<n>_<task>.md` (Status: `draft`).
   - Lege keinen Code an, bevor mindestens die erste Spec vom User abgesegnet ist.
4. Berichte: was wurde angelegt, welche Spec ist als nächstes zu reviewen.

**Nicht** alle Phasen gleichzeitig starten — nur die angegebene.
