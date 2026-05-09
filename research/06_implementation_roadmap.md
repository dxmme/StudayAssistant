# 06 — Implementation Roadmap

> Vom leeren Ordner zum funktionierenden System — in Phasen, mit MVP-Definition, mit klaren Stop-Lights für „kann ich damit lernen, oder noch nicht?"

---

## Strategischer Ansatz

**Build-What-You-Need-Now-First.** Im ersten Semester nutzt du die App tatsächlich. Verschwende keine Zeit mit Nice-to-Haves, bevor der Kern steht. Jede Phase liefert ein **lauffähiges System**, das du *jetzt schon* benutzen kannst.

**Stop-Lights pro Phase:**
- 🟢 Nutzbar fürs nächste Semester
- 🟡 Nutzbar mit manuellen Workarounds
- 🔴 Reine Vorarbeit, noch nicht produktiv

---

## Phase 0 — Foundations (Woche 1)  🔴

> **Ziel:** Repo, Tooling, leere Skeleton-App, Datenbank.

### Tasks
- [ ] Tech-Stack final entscheiden (siehe unten).
- [ ] Repo-Struktur:
  ```
  StudyAssistant/
    backend/         (FastAPI)
    frontend/        (Next.js oder SvelteKit)
    shared/          (Types, Schemas)
    research/        (diese Docs)
    .claude/         (Claude-Code-Konfiguration)
    CLAUDE.md
  ```
- [ ] DB-Schema (siehe `04_system_architecture.md`) als Migration einrichten (Alembic).
- [ ] Health-Endpoint, Auth-Stub (single-user, lokal).
- [ ] Frontend-Skeleton mit Tailwind + KaTeX integriert.
- [ ] LLM-Gateway-Service mit Anthropic-Client + Caching aktiv.
- [ ] Prompt-Cache testweise für einen Coaching-Flow durchspielen.

### Stack-Empfehlung (begründet)

| Layer | Wahl | Alternativen | Begründung |
| --- | --- | --- | --- |
| **Backend** | FastAPI (Python 3.12) | Express, Hono | ML-Ökosystem nativ, easy LLM-Integration |
| **Frontend** | Next.js (App Router) | SvelteKit, Astro | Reife, Vercel-Hosting möglich, gut für PWA |
| **DB** | SQLite + Alembic | Postgres | Lokal-first, später Postgres-Switch trivial |
| **Vector** | Chroma (file-based) | Qdrant lokal | Null-Setup, reicht für 10k-100k Embeddings |
| **PDF-Parser** | `marker-pdf` | `pymupdf` + `nougat` | Math-aware ist Pflicht für ML-Folien |
| **LaTeX-Render** | KaTeX | MathJax | KaTeX ~10× schneller im Browser |
| **LLM** | Anthropic Claude | OpenAI | Beste Math + längster Context (Beweise) |
| **Embeddings** | `text-embedding-3-large` | `bge-m3` lokal | Start: API; Privacy-Switch später |
| **State** | TanStack Query + Zustand | Redux | Modern, lean |
| **Speech** | Web Speech API (Browser) → Whisper API | whisper.cpp lokal | Browser-API für Start, Whisper-API für Quality |

### Output Phase 0

Eine App, die nichts Lernrelevantes kann, aber:
- Du kannst dich einloggen.
- DB existiert.
- LLM-Calls funktionieren mit Caching.

→ Daraus alleine kann man nicht lernen. **🔴**

---

## Phase 1 — MVP Lernkern (Wochen 2–4)  🟡

> **Ziel:** Du kannst Material hochladen, Karten manuell anlegen, sie täglich reviewen (FSRS). Coaching läuft als simpler Chat.

### Was wird gebaut

1. **Material-Upload** (PDFs).
2. **Material-Ingest-Pipeline:** PDF → Chunks → Embeddings → Vector-Store. Konzept-Extraktion *minimal* (per LLM, ohne Kuratierung).
3. **Karten manuell anlegen + bearbeiten** (Markdown + LaTeX). Kein Auto-Generate yet.
4. **FSRS-Scheduler** integriert (`py-fsrs`).
5. **Daily-Review-UI** (Karten umdrehen, 1-4 raten). Vollständig Tastatur-bedienbar.
6. **Sokratisches Coaching** als simpler Chat:
   - Eingabe: aktuelles Konzept (manuell aus Liste).
   - System-Prompt mit Sokrates-Regeln + RAG-Kontext.
   - Streaming-Output.
   - **Noch ohne Diagnostic-Pipeline.**

### Was *nicht* drin ist

- Keine automatische Karten-Generierung.
- Keine Quiz-Engine.
- Keine Plan-Engine — Karten werden nach FSRS-Due gezogen, mehr nicht.
- Keine Worked Examples.
- Keine Mock Exams.

### Stop-Light: 🟡

Du kannst **bereits** lernen. Aber:
- Karten manuell anlegen kostet ~2 min/Karte → ~30-40 min für 15-20 Karten pro Vorlesung.
- Ohne automatische Plan-Generierung musst du Disziplin selbst aufbringen.

→ Trotzdem schon **deutlich** besser als gar kein System. Wenn du bald in ein Semester gehst, kannst du hier stoppen, lernen, und in Pausen weiterbauen.

### Akzeptanzkriterien

- 100 manuell angelegte Karten, 14 Tage Reviews, alle FSRS-Übergänge korrekt.
- Coaching-Session über 10 Turns ohne Bug.
- Material-Suche per Embedding liefert relevante Snippets.

---

## Phase 2 — Auto-Generation + Plan Engine (Wochen 5–7)  🟢

> **Ziel:** Aus einem Foliensatz werden Karten *vorgeschlagen*. Plan-Engine generiert tägliche Sessions. Du verlässt dich aufs System.

### Was wird gebaut

1. **Konzept-Extraktion-Pipeline** (full):
   - LLM extrahiert mit strukturiertem Schema.
   - Konzept-Dedup (Embedding + LLM-Verify).
   - Knowledge-Graph (Prerequisites).
   - Altklausur-Klassifikator (Bloom-Level + Konzept-Tags).
   - User-Review-UI für extrahierte Konzepte.
2. **Karten-Auto-Generation:**
   - Pro Konzept LLM-Vorschläge mit Andy-Matuschak-Regeln.
   - Self-Critique (zweiter LLM-Call).
   - Dedup gegen existierende Karten.
   - **Review-Queue:** Du siehst Vorschläge, akzeptierst/editierst.
3. **Plan-Engine:**
   - Phasen-Allocation (Semester / Active / Consolidation / Final).
   - Tägliche Session-Generierung.
   - Mastery-Tracking.
   - Re-Planning nach jeder Session.
4. **Coaching-Diagnostic:**
   - Strukturierter Diagnostic am Ende jeder Session.
   - Triggert Karten-Generierung für Lücken.
   - Updated Mastery-Scores.
5. **Quiz-Engine (Basis):**
   - Frage-Generierung aus Konzept + RAG.
   - Free-Text-Bewertung per LLM.
   - Multi-Choice + Calc-Type.
   - Interleaving-Logik (Mix aus mehreren Konzepten pro Session).

### Stop-Light: 🟢

Das ist der **Punkt, an dem das System dich tatsächlich entlastet**. Daily-Session-Button reicht; alles andere passiert.

### Akzeptanzkriterien

- 1 Vorlesung von 0 → fertig konfiguriert in < 30 min.
- Plan generiert konsistent Sessions, die ins 60-90-min-Budget passen.
- Quiz-Bewertung deckt sich zu >85 % mit Self-Bewertung (kalibrierter Self-Score-Test).
- Diagnostic identifiziert Lücken, die du auch beim Selbst-Review identifiziert hättest.

---

## Phase 3 — Worked Examples + Beweis-Reconstruction (Wochen 8–10)  🟢

> **Ziel:** Faded Worked Examples für Mathematik. Beweis-Reconstruction-Modus. Tiefes ML-spezifisches Lernen.

### Was wird gebaut

1. **Worked-Example-Engine:**
   - Datenmodell mit Stages (siehe `04`).
   - Auto-Erstellung aus Lehrbuch-Stellen + Übungs-Lösungen via LLM.
   - User-Review (kritisch — diese sind heikler als Karten).
   - Stage-Übergangs-Logik (FSRS-Stability + Quiz-Performance).
2. **Beweis-Reconstruction:**
   - LaTeX-Eingabe-Modus.
   - LLM-Verifier (Schritt-für-Schritt-Vergleich).
   - Sokratische Lücken-Hinweise.
3. **Mini-Coding-Sandbox:**
   - Pyodide im Browser oder Docker-Sandbox.
   - Algorithmus-Implementierungs-Aufgaben (z. B. „implementiere EM in 25 Zeilen").
   - Auto-Test gegen erwartete Outputs.

### Stop-Light: 🟢++

Jetzt funktioniert das System **auf Tübingen-Niveau**.

### Akzeptanzkriterien

- 5 Beweise erfolgreich rekonstruiert in der UI; LLM-Verifier hat keine False-Positives.
- Faded Stages haben pädagogisch sinnvolle Übergänge (manuelle Validation an 10 Beispielen).

---

## Phase 4 — Mock Exam Engine (Wochen 11–12)  🟢++

> **Ziel:** Vollständige Klausur-Simulation. Auswertung. Lückenarbeit-Loop.

### Was wird gebaut

1. **Mock-Exam-Setup:**
   - Pro Fach: Konfiguration (Dauer, Aufgaben-Anzahl, erlaubte Hilfsmittel).
   - Auto-Mix aus Altklausuren-Aufgaben + LLM-generierten ähnlichen Aufgaben.
2. **Klausur-Modus:**
   - Vollbild, Timer, kein Karten-Zugriff.
   - LaTeX-Editor + Whiteboard-Modus optional.
3. **Auswertung:**
   - LLM bewertet aufgabenweise gegen Soll-Lösung.
   - Self-Adjustment: du korrigierst die LLM-Bewertung.
   - Per-Konzept-Score-Breakdown.
4. **Lückenarbeit-Loop:**
   - Schwächste 3 Themen → automatischer Sprint-Plan für nächste 3-5 Tage.
   - Worked Example + Karten + Re-Quiz.

### Stop-Light: 🟢++

Vollständiges System. Du gehst in Klausuren ohne Panik.

---

## Phase 5 — Polish & Daily-Use (laufend)

> Iterativ basierend auf eigener Nutzung.

- Voice-Mode (Whisper-Integration)
- PWA + Mobile-Reviews
- Cheat-Sheet-Generator
- Cross-Course-Knowledge-Graph („wo kommt SVD in Probabilistic ML wieder vor?")
- Konzept-Map als Hauptansicht (Concept-Map-View für Course)
- Backup/Export-Mechanismus
- LLM-Modell-Wechsel je nach Aufgabe (Cost-Optimization)

---

## Risiken & Mitigation

| Risiko | Mitigation |
| --- | --- |
| **LLM phantasiert in Karten / Quiz** | Strikt RAG-grounded. Self-Critique. User-Review-Queue obligatorisch. |
| **Plan-Engine erzeugt zu viel** | Hard-Cap pro Session-Dauer. Karten-Pool pro Tag begrenzt (max 30 due). |
| **FSRS-Optimizer brauchst zu viele Reviews** | Default-Parameter aus 700M-Korpus reichen für die ersten 200 Reviews; Optimizer erst bei >500 Reviews relevant. |
| **PDF-Parsing zerstört Math** | `marker-pdf` (Math-aware). Bei Fehlern manueller LaTeX-Insert. |
| **Konzept-Dedup macht Fehler** | Threshold konservativ. User-Review für Borderline-Fälle. |
| **Du baust statt zu lernen** | Strikte Phasen-Disziplin. Phase 1 muss tatsächlich „benutzbar" sein, nicht „perfekt". |

---

## Build-vs-Use-Trade-off

> Wichtig: Wenn ein Klausurzyklus näher rückt, **stop building, start using**.

**Heuristik:**
- Mehr als 8 Wochen bis Klausuren → Build & Use parallel.
- 4–8 Wochen → 80% Use, 20% Build (nur Bugs).
- Weniger als 4 Wochen → 100% Use. Notizen für später aufschreiben.

---

## Was du *zuerst* baust (konkret morgen)

```
1. mkdir backend frontend shared
2. Backend: FastAPI minimal mit /health.
3. DB: alembic init, courses + materials Tabellen.
4. Frontend: Next.js + Tailwind + KaTeX-Hello-World.
5. LLM-Gateway: Anthropic-Client mit prompt_caching aktiv. Test-Call.
6. PDF-Upload-Endpoint: speichert ins Filesystem, schreibt materials-Row.
```

→ Das ist *eine Woche*. Danach ist der Boden bereit für Phase 1.

---

## Wichtigste „No-Go-Areas" beim Bauen

- ❌ **Nicht** das LLM Antworten direkt geben lassen. Sokrates-Modus ist ein Designprinzip, kein Feature.
- ❌ **Nicht** Karten ohne User-Review in die DB schreiben. Garbage-in propagiert sonst.
- ❌ **Nicht** Mehrere LLM-Provider parallel früh integrieren. Erst Anthropic, später Multi.
- ❌ **Nicht** Mobile-First. Mobile-Sessions sind unrealistisch für Beweise.
- ❌ **Keine** Login-Komplexität. Single-User-lokal reicht.
- ❌ **Keine** Datenbank-Optimierungen vor Phase 4. SQLite reicht für 10k Karten + Reviews.

---

## Erfolgskriterien (am Ende von Phase 4)

Realistische Selbst-Tests:
1. **Onboarding-Test:** Neues Fach von Grund auf in < 30 min konfiguriert.
2. **Daily-Compliance-Test:** 14 Tage in Folge Session-Komplettierung über > 80 %.
3. **Klausur-Outcome-Test:** Klausur in Statistical ML besser als ohne System (subjektiv: weniger Stress, objektiv: Note).
4. **Diagnostic-Accuracy-Test:** LLM-Diagnostic identifiziert die Lücken, die du selbst nach gründlichem Review auch identifiziert hättest, in > 80 %.
5. **Calibration-Test:** Mock-Exam-Score korreliert mit echten Klausur-Score (R² > 0.5 über mehrere Fächer).

---

## Geschätzter Build-Aufwand

| Phase | Aufwand (solo, fokussiert) |
| --- | --- |
| Phase 0 | 1 Woche |
| Phase 1 | 2–3 Wochen |
| Phase 2 | 2–3 Wochen |
| Phase 3 | 2 Wochen |
| Phase 4 | 1–2 Wochen |
| **Gesamt** | **~10–12 Wochen** bei ca. 15-25 h/Woche |

→ Realistisch: über ein Semester bauen, nebenher das System schon mit Phase-1-Funktionalität benutzen.

---

## Nächster konkreter Schritt

**Wenn du willst:** sag „leg mit Phase 0 los" und ich richte Backend-Skeleton + Frontend-Skeleton + DB-Migrations + LLM-Gateway in einem Rutsch ein — mit den hier festgelegten Tech-Entscheidungen. Dann hast du in 1-2 Stunden eine lauffähige Basis und kannst sofort mit Phase 1 starten.

---

*Stand: 2026-05-08. Roadmap wird nach Phase 1 evaluiert und ggf. angepasst.*
