# 03 — Techniken & Tools: Was wir konkret bauen

> Diese Datei ist die Brücke zwischen Theorie (`01`, `02`) und Code (`04`).
> Sie beschreibt **welche** Lernmodalitäten implementiert werden, **wie** sie funktionieren, und **welche bestehenden Bibliotheken/Modelle** die Bausteine liefern.

---

## Die 6 Kern-Lernmodalitäten

| Modalität | Lerntechnik (Theorie-Bezug) | Implementierung |
| --- | --- | --- |
| **1. Karteikarten (Spaced Repetition)** | Retrieval Practice + Spacing | FSRS-Scheduler, eigene Card-DB |
| **2. Active-Recall-Coaching** | Self-Explanation, Elaborative Interrogation, Sokratisch | LLM mit System-Prompt, Diagnose-Pipeline |
| **3. Quiz-Engine** | Practice Testing, Bloom-Level-Targeting, Interleaving | LLM-generierte Fragen + Validierung |
| **4. Worked Examples (Faded)** | Cognitive Load, Worked-Example-Effect, Expertise-Reversal | Strukturierte Templates pro Beispieltyp |
| **5. Beweis-Reconstruction** | Generation Effect, Schritt-Verifikation | LaTeX-Parser + Schritt-Match LLM |
| **6. Mock-Exam-Engine** | Practice Testing unter Realbedingungen | Klausur-Simulation + automatische Auswertung |

---

## 1. Karteikarten — FSRS als Scheduler

### Warum FSRS, nicht SM-2

| Aspekt | SM-2 (klassisch) | FSRS |
| --- | --- | --- |
| Modell | Heuristisch (1985) | ML-Modell auf 700M Reviews trainiert |
| Personalisierung | minimal | adaptiert sich an *deine* Vergessenskurve |
| Reviews für gleichen Retention-Level | mehr | weniger (~20–30%) |
| Verlate Reviews | schlecht behandelt | korrekt eingerechnet |
| Status | Anki-Default bis 23.10 | Anki-Default ab 23.10 (2023+) |

→ Wir nutzen **FSRS direkt als Library**: `pip install fsrs` ([PyPI](https://pypi.org/project/fsrs/), [Repo](https://github.com/open-spaced-repetition/free-spaced-repetition-scheduler)).

### Drei-Komponenten-Modell von FSRS

```
Pro Karte gespeichert:
  - Stability  S   →  Halbwertszeit (Tage bis Retrievability auf 90% sinkt)
  - Difficulty D   →  Wie schwer ist diese Karte intrinsisch
  - Last review t

Bei Review:
  - Retrievability R(t) = 0.9 ^ (Δt / S)
  - Nutzer bewertet (Again / Hard / Good / Easy)
  - Modell aktualisiert (S, D) auf neuer Stability + nächstes Due
  - Optimizer kalibriert die Modellparameter periodisch auf deine Daten
```

### Wie wir das nutzen

- Jede Karteikarte = Row in unserer DB mit FSRS-State.
- Nach jeder Review: `scheduler.review_card(card, rating)` → `next_due`.
- Periodisch (z. B. wöchentlich, oder ab 1000 Reviews): `optimizer.train(history)` → angepasste Parameter.
- **Desired Retention** als User-Setting: 0.85 (entspannt) bis 0.95 (vor Klausur).

### Karten-Templates

Wir unterstützen **5 Karten-Typen** (alle mit Markdown + LaTeX + optional Bildanhang):

```yaml
1. basic:
   front: "Was ist eine Konditionszahl?"
   back:  "κ(A) = ‖A‖ · ‖A⁻¹‖ — Maß für Verstärkung kleiner 
           Eingangs-Störungen zu Ausgangs-Fehler."

2. cloze:
   text: "Eine Matrix A heißt {{c1::positiv definit}}, wenn 
          {{c2::xᵀAx > 0 für alle x ≠ 0}} gilt."

3. concept_diagram:
   prompt: "Zeichne aus dem Kopf das Bias-Variance-Diagramm 
            und beschrifte alle Achsen + Kurven."
   reference_image: bias_variance.png
   self_grade: true

4. derivation:
   problem: "Leite die Posterior für N(x; μ, σ²) Likelihood 
             mit N(μ; μ_0, σ_0²) Prior her."
   solution_steps: [step1.tex, step2.tex, ..., stepN.tex]
   verification: llm_compare

5. proof_skeleton:
   theorem: "Mercer's Theorem"
   skeleton_steps: 3
   key_steps_as_subcards: [card_id_1, card_id_2]
```

### Auto-Generierung (LLM)

- Aus jedem Vorlesungs-Foliensatz: Pipeline schlägt **N/100** Karten vor (Faustregel laut Forschung).
- LLM nutzt **strukturierte Prompts** (Andy-Matuschak-Prinzipien):
  - Eine Idee pro Karte
  - Cloze am Satzende, nicht am Anfang
  - Keine Trivia, keine isolierten Fakten
  - Front und Back nicht redundant
- Der Nutzer sieht **Vorschläge** und akzeptiert / bearbeitet — niemals Auto-Import ohne Review.

### Empfohlene LLM-Wahl für Card-Generierung

- **Hauptmodell:** Claude Sonnet 4.6 oder GPT-4o für Geschwindigkeit + Qualität.
- **Für Beweis-Karten:** stärkeres Reasoning-Modell (Opus / o1) — auch wenn teurer.
- **Embeddings:** `text-embedding-3-large` (OpenAI) oder `bge-m3` lokal — für Duplikat-Detektion zwischen Karten und für RAG.

---

## 2. Active-Recall-Coaching — der LLM-Sokrates

### Ziel

Das LLM ist **kein Lehrer**, der Antworten gibt. Es ist ein **Sokrates**, der dich Antworten *produzieren* lässt und Lücken **diagnostiziert**.

### Beispiel-Session

```
SYSTEM: Du bist ein sokratischer Tutor für Machine Learning auf 
        Master-Niveau. Gib niemals direkte Antworten. Stelle Rückfragen.
        Identifiziere die größte Lücke in der Argumentation des Studierenden.
        Wenn er stuck ist: kleinster mögliche Hinweis, kein Ausschütten der Lösung.

USER: Ich erkläre dir SVD. Die SVD zerlegt eine Matrix A in U Σ Vᵀ, wobei U und V 
      orthogonal sind und Σ Diagonalmatrix ist mit den Singulärwerten.

LLM:  Gut, das ist die Definition. Was ist die geometrische Interpretation? 
      Wenn ich einen Vektor x mit A multipliziere, was passiert in den drei Schritten?

USER: Vᵀ rotiert, Σ skaliert, U rotiert nochmal.

LLM:  Genau. Eine Frage zur Tiefe: Warum sind die Singulärwerte immer ≥ 0, 
      aber Eigenwerte können negativ sein?

USER: Weil... äh, weil Σ eine Diagonalmatrix mit nicht-negativen Einträgen ist?

LLM:  Das ist Wirkung, nicht Ursache. Welche Matrix steht hinter den 
      Singulärwerten — was sind sie *Wurzeln von*?

USER: AᵀA?

LLM:  Genau. Und welche Eigenschaft hat AᵀA, die garantiert, dass alle 
      Eigenwerte ≥ 0 sind?

USER: Positiv semidefinit, weil xᵀAᵀAx = ‖Ax‖² ≥ 0.

LLM:  Perfekt. Du hast jetzt den Kern verbunden. ✓ 
      Lücke geschlossen: Warum SVD numerisch stabiler ist als Eigenzerlegung 
      hast du noch nicht erwähnt — wollen wir da weitermachen?
```

### System-Prompt-Skelett

```
ROLE: Sokratischer Tutor für [Fachgebiet] auf [Niveau].
KONTEXT: Folgender Vorlesungsstoff wurde behandelt: [RAG-Snippets].
KONZEPT IM FOKUS: [aktuelles Konzept aus dem Plan].
ZIEL-BLOOM-LEVEL: [aus Konzept-Metadaten].

REGELN:
1. Niemals die Antwort komplett ausschütten.
2. Bei jeder Antwort des Nutzers: identifiziere die größte logische Lücke
   ODER bestätige Korrektheit.
3. Bei Stuck: kleinster nicht-trivialer Hinweis.
4. Verwende die exakte Notation aus dem Vorlesungsmaterial (RAG).
5. Am Ende: Zusammenfassung "Du hast verstanden: ...; offene Lücken: ..."

OUTPUT: Markdown mit LaTeX, knapp.
```

### Diagnose-Output

Nach jeder Coaching-Session schreibt das LLM ein **strukturiertes Diagnostic** in die DB:

```yaml
session_id: "2026-05-08_svd_recall"
topic: "SVD"
gaps_identified:
  - "Numerische Stabilität SVD vs. EVD nicht erklärt"
  - "Verbindung zu Konditionszahl unklar"
mastered:
  - "Definition der SVD"
  - "Geometrische Interpretation"
  - "PSD-Eigenschaft von AᵀA"
recommended_actions:
  - generate_card: "Warum κ(AᵀA) = κ(A)²?"
  - revisit_worked_example: "stability_svd_vs_evd"
```

→ Dieses Diagnostic füttert den **Plan-Update-Mechanismus**: schwache Konzepte → höhere Frequenz, neue Karten, Worked Examples.

---

## 3. Quiz-Engine

### Generierungs-Strategie

Pro Konzept werden Fragen generiert, die **alle relevanten Bloom-Levels** abdecken:

```
Konzept: Backpropagation
Aus Altklausur klassifiziert: Bloom-Level 3 (Apply), 4 (Analyze)
→ Quiz-Mix: 30% Apply (Berechnung), 50% Analyze (Diagnose), 20% Verstehen
```

### Frage-Typen

| Typ | Gut für Bloom-Level | Beispiel |
| --- | --- | --- |
| **Multiple Choice** | 1 (Remember), 2 (Understand) | "Welche Aussage über RKHS ist korrekt?" |
| **Free Text Short** | 2, 3 | "Erkläre in 2 Sätzen, warum SVD stabil ist." |
| **Calculation** | 3 (Apply) | "Berechne die SVD von [[1,1],[0,1]]." |
| **Diagnose-Frage** | 4 (Analyze) | "Warum funktioniert SGD hier nicht?" |
| **Vergleichs-Frage** | 5 (Evaluate) | "Wann ist EVD besser als SVD?" |
| **Open Construction** | 6 (Create) | "Schlage eine Variante von Adam vor, die ..." |

### Validierung — der schwierige Teil

Das LLM generiert Fragen + Soll-Antworten. Das ist *nicht* trivial korrekt. Lösung:

1. **Grounding über RAG:** Frage *muss* mit Skript-Snippet gegrounded sein.
2. **Cross-Check:** Zweites LLM (oder gleiche Modell, anderer Prompt) verifiziert die Soll-Antwort.
3. **User Flagging:** Nutzer kann jede Frage als „falsch / unklar" flaggen → wird zur Review-Queue.
4. **Distillation aus Altklausuren:** Wo möglich, werden *echte* Altklausurfragen als Goldstandard verwendet.

### Bewertungs-LLM (für Free-Text-Antworten)

```
PROMPT (Bewertung):
  Frage: [Q]
  Soll-Antwort (gefunden im Skript, Seite N): [A_correct]
  Nutzer-Antwort: [A_user]
  
  Bewerte:
  - correctness: 0-1 (komplett richtig)
  - completeness: 0-1 (alle wichtigen Punkte)
  - precision_of_terminology: 0-1
  
  Identifiziere fehlende Punkte und vergleiche Begriffsverwendung.
```

→ Output wird genutzt für:
- Quiz-Score (normalisiert).
- Gap-Detection (welche Konzepte sind schwach).
- FSRS-Rating für die zugehörigen Karten (Again / Hard / Good / Easy ableitbar).

---

## 4. Worked Examples (Faded)

### Datenmodell

```yaml
id: "we_posterior_gauss"
title: "Posterior Herleitung: Gauss × Gauss"
prerequisites: ["bayes_rule", "gauss_density"]
target_bloom: 3
steps:
  - step_id: 1
    text: "Schreibe Bayes' Regel auf: p(μ|x) ∝ p(x|μ) p(μ)"
    type: setup
    fade_at: never
  - step_id: 2
    text: "Setze Likelihood ein: ∝ exp(-(x-μ)²/(2σ²))"
    type: substitution
    fade_at: stage2
  - step_id: 3
    text: "Setze Prior ein: ∝ exp(-(x-μ)²/(2σ²)) · exp(-(μ-μ₀)²/(2σ₀²))"
    type: substitution
    fade_at: stage2
  - step_id: 4
    text: "Quadratisch in μ ergänzen ..."
    type: algebra
    fade_at: stage1
  ...
```

### Faded-Mode-Logik

- **Stage 0 (Worked):** Alle Schritte gezeigt + Self-Explanation-Prompts pro Schritt.
- **Stage 1 (Faded I):** Algebra-Schritte ausgeblendet, Setup gezeigt.
- **Stage 2 (Faded II):** Nur Setup + Endergebnis sichtbar, Mitte fehlt.
- **Stage 3 (Free):** Nur Aufgabe + Lösung am Ende. Du löst komplett selbst.

→ Übergang Stage k → Stage k+1, wenn FSRS-Stability > Schwellwert *oder* Quiz-Performance > 0.8 für 2 aufeinanderfolgende Sessions.

---

## 5. Beweis-Reconstruction

### Workflow

1. Nutzer wählt Theorem / Lemma / Proposition.
2. System zeigt Aussage + Voraussetzungen, **nicht** den Beweis.
3. Nutzer tippt / spricht den Beweis.
4. Parser zerlegt in atomare Schritte (LaTeX-Strukturen, Implikationen, Gleichungen).
5. LLM-Verifier vergleicht jeden Schritt mit der Skript-Version (RAG).
6. Output:
   - ✅ Schritte, die korrekt sind.
   - ⚠️ Schritte, die unklar / falsch sind → Sokratische Rückfrage.
   - 🚫 Vergessene Voraussetzungen.

### Beispiel-Output

```
Dein Beweis von Mercer's Theorem:
✅ T_k ist linear (trivial gezeigt).
✅ T_k ist beschränkt (du nutzt Cauchy-Schwarz korrekt).
⚠️ "T_k ist kompakt" — du sagst es, aber zeigst es nicht. 
    Welche Eigenschaft des Kerns brauchst du?  (→ Hilbert-Schmidt)
🚫 Voraussetzung "k stetig auf [0,1]² kompakt" wurde nirgends benutzt — 
    aber sie ist nötig für L²-Beschränktheit von k.
```

→ Sokratischer Modus: keine Antwort, nur Pointer + Hinweis auf die Lücke.

---

## 6. Mock-Exam-Engine

### Modus

- **Vollständige Klausur** im echten Format des jeweiligen Lehrstuhls (PDF-Generator + Online-Modus).
- Timer aktiv, keine Karten-Reviews zugelassen.
- Optional: Skript-Zugriff (wie in der echten Klausur).
- Nach Abgabe: **automatische Vorbewertung** (LLM) + manuelle Korrektur durch dich (kalibriertes Self-Scoring).

### Erkenntnis-Loop

```
Mock 1 (Phase 3 Start)
  Score: 65%
  Schwächste Themen: [SVD-Stabilität, EM-Konvergenz, Causal Discovery]

→ System erstellt:
  - 12 neue Karten zu diesen Themen
  - 2 Worked Examples
  - 1 Active-Recall-Session pro Thema
  - Plan: nächste 5 Tage Schwerpunkt auf diesen 3 Themen

Mock 2 (3 Tage später)
  Score: 78%
  Schwächste Themen: [SVD-Stabilität verbessert, Causal Discovery noch schwach, neu: PAC-Bounds]
  
  → Weitere Iteration.

Mock 3 (Klausur-Woche)
  Score: 85%+ → bereit.
```

---

## Tooling-Stack (Übersicht)

| Layer | Auswahl | Begründung |
| --- | --- | --- |
| **Spaced-Repetition-Algorithmus** | `py-fsrs` | State-of-the-Art, gut dokumentiert |
| **LLM (Sokratisch + Generierung)** | Claude Sonnet 4.6 (Standard) / Opus für Beweise | Beste Quality-Cost-Ratio, gute Math-Skills, 200k Context |
| **Embeddings** | `text-embedding-3-large` oder `bge-m3` lokal | Karten-Dedup + RAG |
| **Vector Store** | `chroma` (lokal) oder `qdrant` | Einfach, lokal hostbar |
| **PDF/Folien-Ingest** | `pymupdf` + `marker-pdf` (Math-aware) oder `unstructured.io` | Math-Notation behalten |
| **LaTeX-Rendering** | KaTeX (Frontend) | Schnell, klausurnah |
| **Backend** | Python (FastAPI) | Standard, schnelle ML-Integration |
| **Frontend** | Next.js + Tailwind oder SvelteKit | Schlank, web-nativ |
| **DB** | SQLite (Start) → Postgres | Lokal-first, einfach |
| **Hosting** | Lokal (Privacy) → optional VPS | Materialien sind sensibel |

> Empfehlung: **lokal-first**, weil Vorlesungsmaterialien sensibel sein können und du LLM-Calls über die jeweilige API abrechnest (nicht per VPS-Hosting).

---

## Wichtige Anti-Pattern beim Bauen

- ❌ **Auto-Import** generierter Karten ohne Review → Garbage propagiert.
- ❌ LLM **als Antwortmaschine** statt Sokrates → erlernte Hilflosigkeit.
- ❌ **Gamification** (Streaks, Punkte, Badges) → trainiert das falsche Reward-System.
- ❌ **Zu viele Karten** generieren → führt zu Review-Burnout und schlechter Performance.
- ❌ **Falsche Difficulty-Annahmen** → ohne Expertise-Reversal-Awareness wird das System schnell langweilig oder überfordernd.
- ❌ **Kein Grounding** in eigenen Folien → das LLM phantasiert mit anderer Notation und verwirrt dich.

---

*Stand: 2026-05-08. Tool-Stack wird in der Architektur (`04`) konkretisiert.*
