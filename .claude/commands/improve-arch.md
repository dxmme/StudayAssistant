---
description: Scanne Codebase nach Architektur-Verbesserungskandidaten (Deep Modules Prinzip)
---

# /improve-arch

Scanne die StudyAssistant-Codebase nach Stellen die gegen das Deep-Modules-Prinzip verstoßen
oder die Software-Entropie erhöhen.

## Vorgehen

1. Scanne `backend/app/` und `frontend/`:

   **Shallow-Module-Kandidaten (Backend):**
   - Files mit <30 Zeilen die nur 1 Funktion/Klasse enthalten
   - Service-Files die immer zusammen geändert werden
   - Router-Files mit nur 1-2 Endpoints

   **Shallow-Module-Kandidaten (Frontend):**
   - Komponenten <20 Zeilen die nirgendwo sonst genutzt werden
   - Pages die direkt DB-nahe Logik enthalten (sollte in Hooks/Services)

   **Coupling-Probleme:**
   - Imports die Schichten überspringen (Frontend → DB, Service → API)
   - Circular Imports
   - God-Files (>500 Zeilen mit gemischten Verantwortlichkeiten)

2. Überprüfe Stack-spezifische Patterns:

   **Backend-Checks:**
   - Alle Models in `db/models/` — kein Modell-Code in `api/` oder `services/`?
   - `LLMGateway` als einziger Anthropic-Einstiegspunkt?
   - Kein direkter `anthropic.Anthropic()` außerhalb von `services/llm_gateway.py`?
   - Settings nur über `core/config.py` (Dependency Injection)?

   **Frontend-Checks:**
   - Server-Components vs. Client-Components korrekt getrennt?
   - `<Math>` Komponente als einziger KaTeX-Einstiegspunkt?
   - Kein `dangerouslySetInnerHTML` außerhalb von `Math.tsx`?
   - Keine `any` Types?

3. Erstelle Bericht mit:
   - Liste der Kandidaten (Datei + Problem + Empfehlung)
   - Priorisierung: welches verursacht die meiste Entropie?
   - Konkreter Refaktor-Vorschlag für Top-3

**Implementiere nichts.** Der Bericht geht zurück an den User für Entscheidung.
Wenn Refaktor gewünscht: erst `/spec arch-refactor-<name>` schreiben.
