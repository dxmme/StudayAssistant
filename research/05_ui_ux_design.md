# 05 — UI/UX-Design

> **Designziel:** *Eine* Hauptansicht. *Ein* Daily-Flow. Kein Pop-up-Theater, keine Streak-Counter. Du öffnest morgens die App, machst deine Session, schließt sie. Das war's.

---

## Design-Prinzipien

1. **Default-Pfad ist der Lernpfad.** App öffnen = sofort die heutige Session sehen.
2. **Keine Gamification.** Streaks/XP triggern das falsche Reward-System (Performance-Show statt Lernen). Der Reward ist die Klausur.
3. **Konzentration > Scrolling.** Während einer Session ist *alles andere weg* — kein Sidebar, keine Notifications.
4. **Erkennbarkeit über Erinnerung.** Du sollst nie nachdenken müssen, was die App will. Buttons heißen, was sie tun.
5. **Mathematik first-class.** LaTeX-Eingabe und -Anzeige sind nicht Nachgedanke, sondern Kern.
6. **Tastaturbedienbar.** Jede Aktion hat ein Shortcut. Maus optional.

---

## Information Architecture

```
┌── Dashboard (Default-View)
│    ├─ Heutige Session (großes Karten-UI)
│    ├─ Pro Fach: Status (Phase, Tage bis Klausur, Mastery)
│    └─ Schnellaktionen (Material hochladen, Karten generieren, ...)
│
├── Course (pro Fach)
│    ├─ Materials (Folien, Skript, Altklausuren)
│    ├─ Concepts (Knowledge-Graph-View)
│    ├─ Cards (Liste, Filter, Bulk-Edit)
│    ├─ Plan (Kalenderansicht der nächsten 4 Wochen)
│    └─ Mock Exams (Liste + neue starten)
│
├── Session (in-progress, Vollbild-Modus)
│    ├─ Card Review (FSRS)
│    ├─ Worked Example (mit Self-Explanation-Prompts)
│    ├─ Coaching Chat
│    ├─ Quiz
│    └─ Mock Exam
│
└── Settings (minimal)
     ├─ Tagesbudget pro Fach
     ├─ Zielretention (FSRS)
     ├─ LLM-API-Key
     └─ Export / Backup
```

---

## Daily Flow (der Hauptpfad)

```
┌─────────────────────────────────────────────────────────────────────┐
│  StudyAssistant                                          ⚙          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Heute, Donnerstag 8. Mai                            85 min geplant │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  Statistical ML                       Klausur in 38 Tagen  │     │
│  │  Phase: Active Preparation              Mastery 67%        │     │
│  │                                                            │     │
│  │   ▶  Session starten  (60 min)                             │     │
│  │      ─ 25 fällige Karten                                   │     │
│  │      ─ Neues Konzept: VC-Dimension                         │     │
│  │      ─ Coaching: PAC-Bound Beweis                          │     │
│  │      ─ Interleaved Quiz (5 Fragen)                         │     │
│  └────────────────────────────────────────────────────────────┘     │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  Probabilistic ML                   Klausur in 47 Tagen    │     │
│  │  Phase: Semester Companion           Mastery 41%           │     │
│  │   ▶  Session starten  (25 min)                             │     │
│  └────────────────────────────────────────────────────────────┘     │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  +  Neues Fach hinzufügen                                  │     │
│  └────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

→ Du klickst „Session starten". Alles andere passiert in der Session.

---

## Session-Screens

### A. Karten-Review

```
┌─────────────────────────────────────────────────────────────────────┐
│  Statistical ML  ·  Karte 7 von 25                          ✕ Pause │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│                                                                     │
│        Was ist die VC-Dimension einer Hypothesenklasse H?           │
│                                                                     │
│                                                                     │
│                                                                     │
│                                                                     │
│  ┌────────────────────────────────────────┐                         │
│  │   Antwort zeigen   (Leertaste)         │                         │
│  └────────────────────────────────────────┘                         │
└─────────────────────────────────────────────────────────────────────┘
```

Nach Anzeige:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Statistical ML  ·  Karte 7 von 25                          ✕ Pause │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│        Was ist die VC-Dimension einer Hypothesenklasse H?           │
│                                                                     │
│  ─────────────────────────────────────────────────────────          │
│                                                                     │
│  Größte Anzahl Punkte d, sodass H jede mögliche Beschriftung        │
│  von d Punkten realisieren kann ("shattern").                       │
│                                                                     │
│  Beispiel: Lineare Klassifikatoren in ℝᵈ haben VC-Dim = d+1.        │
│                                                                     │
│  ┌──────────┬──────────┬──────────┬──────────┐                     │
│  │  Again   │  Hard    │  Good    │  Easy    │                     │
│  │   (1)    │   (2)    │   (3)    │   (4)    │                     │
│  └──────────┴──────────┴──────────┴──────────┘                     │
│                                                                     │
│  Kommentar: "Ich erinnere die Definition, aber das Beispiel war     │
│              nicht parat."                                          │
└─────────────────────────────────────────────────────────────────────┘
```

→ Tasten 1–4 für Rating. Optional: Kommentar (per `/`-Slash-Befehl).

### B. Coaching-Session (Sokratisches Chat)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Coaching: PAC-Bound Beweis                                ✕ Beenden│
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  COACH                                                              │
│  Erkläre mir die Hauptidee des PAC-Bounds für endliche             │
│  Hypothesenklassen. Beginne mit dem Aufbau, nicht den Details.      │
│                                                                     │
│  DU                                                                 │
│  Wir wollen eine Schranke, dass mit hoher Wahrscheinlichkeit        │
│  ein Klassifikator mit kleinem Trainingsfehler auch kleinen         │
│  echten Fehler hat.                                                 │
│                                                                     │
│  COACH                                                              │
│  Gut. Welche Werkzeug-Idee verbindet "Trainingsfehler" mit          │
│  "echtem Fehler"?                                                   │
│                                                                     │
│  DU                                                                 │
│  ▌                                                                  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │ Antwort schreiben (LaTeX mit $...$, Mikrofon: Strg+M)    │      │
│  └──────────────────────────────────────────────────────────┘      │
│                                                                     │
│  💡 Hinweis bekommen (Strg+H — kostet kein Lernen)                  │
└─────────────────────────────────────────────────────────────────────┘
```

→ Bei Session-Ende sieht der Nutzer das Diagnostic:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Coaching beendet · 12 min                                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ✓  Verstanden                                                      │
│     ─ Definition empirischer vs. echter Fehler                      │
│     ─ Idee der Union Bound                                          │
│                                                                     │
│  ⚠  Lücken                                                          │
│     ─ "Hoeffding-Ungleichung wurde benutzt aber nicht begründet"    │
│     ─ "Komplexität |H| → ln|H|: Schritt nicht klar"                 │
│                                                                     │
│  Aktionen (automatisch eingeplant):                                 │
│     ─ 2 neue Karten zu Hoeffding                                    │
│     ─ Worked Example „Union Bound + Hoeffding" morgen               │
│                                                                     │
│  [ OK, weiter ]                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### C. Quiz

```
┌─────────────────────────────────────────────────────────────────────┐
│  Quiz · Frage 3 von 5                                       ✕ Pause │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Konzept: VC-Dimension                            Bloom: Analyze    │
│                                                                     │
│  Gegeben sei H = {alle Achsenparallelen Rechtecke in ℝ²}.           │
│  Bestimme die VC-Dimension von H und begründe, warum sie nicht      │
│  größer sein kann.                                                  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │ Deine Antwort (LaTeX-Support)                            │      │
│  │                                                          │      │
│  │ VCdim(H) = 4. Vier Punkte in einem "+" können geshattert │      │
│  │ werden. Bei 5 Punkten ...                                │      │
│  └──────────────────────────────────────────────────────────┘      │
│                                                                     │
│  [ Antworten und weiter ]                                           │
└─────────────────────────────────────────────────────────────────────┘
```

Nach Bewertung:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Frage 3 von 5  ·  Score: 0.7 / 1.0                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ✓ Korrekt: VCdim(H) = 4. Vier-Punkt-"+"-Konstruktion ist gültig.   │
│                                                                     │
│  ⚠ Fehlend: Begründung, warum 5 Punkte nicht shatterbar sind.       │
│     Idee: 5 Punkte in konvexer Position — innerstes Punkt kann      │
│     nicht durch achsenparalleles Rechteck isoliert werden.          │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  Karte erstellen aus dieser Lücke?     [ Ja ]   [ Später ] │     │
│  └────────────────────────────────────────────────────────────┘     │
│                                                                     │
│  [ Weiter zu Frage 4 → ]                                            │
└─────────────────────────────────────────────────────────────────────┘
```

### D. Worked Example mit Faded Stages

```
┌─────────────────────────────────────────────────────────────────────┐
│  Worked Example · Posterior Gauss × Gauss          Stage 1 (Faded) │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Aufgabe: Leite die Posterior für N(x; μ, σ²) Likelihood mit        │
│  N(μ; μ_0, σ_0²) Prior her.                                         │
│                                                                     │
│  Schritt 1 (gegeben):                                               │
│   p(μ|x) ∝ p(x|μ) · p(μ)                                            │
│                                                                     │
│  Schritt 2 (gegeben):                                               │
│   ∝ exp(-(x-μ)²/(2σ²)) · exp(-(μ-μ₀)²/(2σ₀²))                       │
│                                                                     │
│  Schritt 3 (DEINE AUFGABE):                                         │
│   Quadratisch in μ ergänzen.                                        │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │ Deine Lösung (LaTeX)                                     │      │
│  │                                                          │      │
│  └──────────────────────────────────────────────────────────┘      │
│                                                                     │
│  💡 Hinweis (S — Pre-Cost: Schritt zählt als „Hard")                │
│  ✓ Ich habe es                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### E. Mock Exam

```
┌─────────────────────────────────────────────────────────────────────┐
│  Mock Exam · SS24 (Statistical ML)               75:23 / 90:00      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Aufgabe 4 von 6  (15 Punkte)                                       │
│                                                                     │
│  Sei H die Klasse aller Halbräume in ℝ³. Zeige, dass VCdim(H) = 4. │
│                                                                     │
│  (a) [5P] Konstruiere eine Punktmenge der Größe 4, die              │
│      H shattert.                                                    │
│                                                                     │
│  (b) [10P] Zeige, dass H keine 5 Punkte shattert.                   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │ Deine Lösung (LaTeX)                                     │      │
│  │                                                          │      │
│  │                                                          │      │
│  │                                                          │      │
│  │                                                          │      │
│  └──────────────────────────────────────────────────────────┘      │
│                                                                     │
│  [ ← Vorige  ]    [ Markieren ]    [ Nächste → ]                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Course-View (außerhalb der Session)

### Concept-Map / Knowledge-Graph

```
┌─────────────────────────────────────────────────────────────────────┐
│  Statistical ML · Concepts                                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│         ┌────────────┐                                              │
│         │   Bayes'   │                                              │
│         │   Theorem  │                                              │
│         └─────┬──────┘                                              │
│               │                                                     │
│       ┌───────┴───────┐                                             │
│       ▼               ▼                                             │
│   ┌───────┐       ┌─────────┐                                       │
│   │  MAP  │       │ Bayes-  │       ●  beherrscht (Mastery > 0.85)  │
│   │       │       │ Risk    │       ◐  in Bearbeitung                │
│   └───┬───┘       └────┬────┘       ○  noch nicht behandelt         │
│       │                │            ⚠  schwach (Mastery < 0.5)       │
│       ▼                ▼                                            │
│      ●               ◐                                              │
│   ...                                                               │
│                                                                     │
│  [ Filter: nur schwache zeigen ]   [ Reset Layout ]                 │
└─────────────────────────────────────────────────────────────────────┘
```

→ Klick auf Knoten öffnet Konzept-Detail (Karten, Worked Examples, Quiz-History dazu).

### Materialien-Upload

```
┌─────────────────────────────────────────────────────────────────────┐
│  Statistical ML · Materialien                                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Vorlesungsfolien                                                   │
│   ✓ vl01_introduction.pdf       42 Seiten   indexiert               │
│   ✓ vl02_pac_learning.pdf       38 Seiten   indexiert               │
│   ⚙ vl03_vc_dimension.pdf       45 Seiten   wird verarbeitet... 78% │
│                                                                     │
│  Skripte                                                            │
│   ✓ skript_v2.pdf               210 Seiten  indexiert               │
│                                                                     │
│  Altklausuren                                                       │
│   ✓ klausur_ss23.pdf  6 Aufgaben · 21 Bloom-Tags · 18 Konzepte      │
│   ✓ klausur_ws22.pdf  6 Aufgaben · 19 Bloom-Tags · 17 Konzepte      │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │  + Hochladen (drag & drop oder Klicken)                  │      │
│  └──────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Onboarding (einmalig pro Fach)

3 Schritte. Mehr nicht.

```
Schritt 1 — Fach anlegen
  Name: ___________________
  Klausurdatum: ____________
  Erlaubte Hilfsmittel in der Klausur: ____________

Schritt 2 — Materialien hochladen
  [Drop alles rein: Folien, Skript, Altklausuren, Themenliste]
  System verarbeitet im Hintergrund.

Schritt 3 — Konzept-Liste reviewen
  System zeigt extrahierte Konzepte. Du:
   - bestätigst, ergänzt, löscht
   - markierst Klausur-Schwerpunkte
  → Plan wird generiert.

Done. Morgen erste Session.
```

---

## Tastatur-Shortcuts (überall verfügbar)

| Taste | Aktion |
| --- | --- |
| `Space` | Karte umdrehen / weiter |
| `1` `2` `3` `4` | Karten-Rating Again / Hard / Good / Easy |
| `Ctrl+M` | Mikrofon (Coaching: spreche statt zu tippen) |
| `Ctrl+H` | Hinweis (kostet Punkt) |
| `Ctrl+S` | Session pausieren |
| `Ctrl+/` | Card aus Lücke erstellen |
| `Esc` | Aus Vollbild-Session zurück |
| `g h` | Go to Home |
| `g c` | Go to Courses |

---

## Was bewusst *fehlt*

- ❌ Keine Streaks, XP, Badges, Leaderboards.
- ❌ Keine Push-Notifications „Du hast heute noch nicht gelernt!".
- ❌ Keine Hilfe-Sidebar mit Tutorials. Tooltips beim ersten Mal reichen.
- ❌ Keine Social-Features.
- ❌ Keine Werbung für „andere Fächer" oder Kurse.
- ❌ Kein Settings-Maximalismus. Nur was wirklich nötig ist.

→ Das System lebt davon, dass du **anstrengende Sessions** durchziehst. Alles, was den Fokus von der Anstrengung wegnimmt, schadet dem Lernen.

---

## Mobile?

- **Phase 1:** Web only. Reviews unterwegs ist verlockend, aber Beweis-Reconstruction auf Mobile ist Pain.
- **Phase 2 (PWA):** Karten-Reviews-only-Modus auf Mobile. Sessions bleiben Desktop.

---

## Audio / Voice Mode

Beim Coaching ist die Option, statt zu tippen zu **sprechen**, sehr wertvoll — du formulierst freier, das LLM transkribiert und reagiert. Whisper API oder lokales `whisper.cpp`. Push-to-talk per `Ctrl+M`.

→ Bonus: Du kannst Coaching-Sessions auch *unterwegs* via Audio machen (Kopfhörer + Phone), das System spielt Frage vor, du antwortest mündlich, Audio wird transkribiert und bewertet. Sehr nah an einer mündlichen Prüfung — ideale Vorbereitung.

---

*Stand: 2026-05-08. UI-Mocks werden in Phase 2 (`06`) als Figma-Sketches verfeinert.*
