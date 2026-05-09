---
description: Alignment-Interview vor einer Implementierung — Claude befragt dich systematisch
---

# /grill-me <feature>

Führe ein systematisches Interview durch, bevor auch nur eine Zeile Code geschrieben wird.

## Vorgehen

1. Lies zuerst:
   - `CLAUDE.md` (Scope, Regeln, Tech-Stack)
   - `.claude/GLOSSARY.md` (Domänen-Vokabular)
   - Die relevante Research-Doc (`research/04_system_architecture.md` für Backend, `research/05_ui_ux_design.md` für Frontend)
   - Falls eine Spec existiert: `specs/<feature>.md`

2. Starte das Interview. Gehe jeden Ast des Entscheidungsbaums durch:

   **Datenmodell:**
   - Welche bestehenden Models sind betroffen?
   - Neue Felder / neue Tabelle notwendig?
   - Welche Alembic-Migration wird gebraucht?
   - Foreign Key Beziehungen? (`ondelete="CASCADE"`?)

   **API-Surface (Backend):**
   - Welche Endpoints (Methode, Pfad, Request/Response)?
   - Authentifizierung benötigt?
   - Welcher LLM-Tier (falls LLM involviert)?
   - Prompt Caching sinnvoll (statischer Kontext)?

   **Frontend:**
   - Neue Route oder bestehende erweitern?
   - Neue Komponenten? (Naming nach UX-Konzept)
   - KaTeX/Mathe-Content dabei?
   - Keyboard-Navigation (Daily-Review: 1-4)?

   **Edge Cases & Fehler:**
   - Leere States (kein Material, keine Cards)?
   - LLM-Fehler (529 Retry, leere Response)?
   - User-Review-Queue nötig? (Kein Auto-Save!)

   **Out of Scope (Phase-1-Ausschlüsse):**
   - Auto-Karten-Generierung? → Nein
   - Gamification? → Nein
   - Mobile-First? → Nein
   - Coaching-Diagnostic? → Nein (Phase 2)

3. Fasse am Ende zusammen:
   - Entschiedene Design-Choices
   - Offene Fragen (für Spec)
   - Abhängigkeiten zu anderen Specs

**Nicht implementieren.** Das Ziel ist das gemeinsame Verständnis, nicht der Code.
Nächster Schritt: `/spec <feature>` wenn Alignment erreicht.
