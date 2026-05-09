# StudyAssistant — Gesamtkonzept

> Ein persönlicher Lernassistent, der den **Organisations-Overhead** aus dem Studium nimmt.
> Du lieferst die Vorlesungsmaterialien (Folien, Skripte, Altklausuren, Themenliste). Das System liefert: einen **wissenschaftlich fundierten, individuell zugeschnittenen Lernplan**, **Active-Recall-Sessions**, **Spaced-Repetition-Karteikarten**, **Quizze**, und ein **Coaching-LLM**, das dich Konzepte erklären lässt und Lücken aufzeigt.

---

## Vision

> *"Ich öffne morgens die App, sehe genau was ich heute lerne (90 min), arbeite die Session strukturiert durch (Recall + Quiz + Coaching), schließe ab und weiß: heute war optimal. Wenn die Klausur kommt, bin ich vorbereitet — ohne Cramming, ohne Chaos, ohne Lücken."*

## Die fünf Designprinzipien

1. **Forschungsbasiert** — Alles, was wir bauen, hat empirische Evidenz (Effect Size > 0.4 in Meta-Analysen). Keine Pop-Pädagogik.
2. **Aktiv statt passiv** — Wiederlesen und Markieren bringen kaum etwas. Retrieval Practice ist der härteste Hebel (g ≈ 0.50–0.61).
3. **Auf den Kurs zugeschnitten** — Was Tübingens Statistical ML verlangt, ist anders als ein BWL-Kurs. Wir analysieren Folien + Altklausuren und leiten daraus die *konkreten* Lernziele auf Bloom-Ebenen ab.
4. **Desirable Difficulties** — Das System darf sich anstrengend anfühlen. Anstrengung ist der Indikator dafür, dass das Hirn arbeitet (Bjork).
5. **So einfach wie möglich** — Eine UI, ein Daily-Flow, eine Stunde pro Tag. Mehr Schalter = weniger Nutzung.

---

## Was das System tut (Endzustand)

### Pro Fach (z. B. „Statistical Machine Learning")

1. **Ingest** — Du lädst alle Vorlesungsfolien, Skripte, Altklausuren, Themenübersicht hoch.
2. **Analyse** — Das System extrahiert Konzepte, baut eine Wissens-Graph-Struktur, klassifiziert die Klausurfragen nach Bloom-Level und schätzt die Klausuranforderungen ein.
3. **Plan** — Es generiert einen Semesterplan: welche Konzepte wann, in welcher Reihenfolge, mit welcher Intensität, mit welchem Ziel-Bloom-Level.
4. **Daily Sessions** — Jeden Lerntag bekommst du eine Session (45–120 min):
   - **Warm-up:** fällige Karteikarten (FSRS).
   - **New Material:** ein neuer Themenblock mit Worked Example + Self-Explanation Prompts.
   - **Active Recall:** Du erklärst das Konzept dem LLM, das Lücken in deiner Argumentation aufzeigt.
   - **Quiz:** 3–5 Fragen genau auf Klausurniveau, gemischt aus den letzten Tagen (Interleaving).
   - **Reflexion:** Was war schwer? Wird in Plan eingearbeitet.
5. **Mock-Exam-Phase** — Letzte 2–3 Wochen vor der Klausur: vollständige Altklausuren unter Zeitdruck, gefolgt von gezielter Lückenarbeit.

---

## Dokumenten-Navigation

| Datei | Inhalt |
| --- | --- |
| **`00_OVERVIEW.md`** *(dieses Dokument)* | Vision, Prinzipien, Navigation |
| **`01_learning_science.md`** | Theorie: warum funktioniert das? Active Recall, Spaced Repetition, Interleaving, Desirable Difficulties, Cognitive Load, Dual Coding, Bloom |
| **`02_ml_master_specifics.md`** | Anpassung auf den ML-Master Tübingen: mathematische Inhalte, Beweise, Probabilistic ML, Deep Learning, Kernel Methods |
| **`03_techniques_and_tools.md`** | Konkrete Lerntechniken: FSRS-Algorithmus, LLM-basierte Karteikartengenerierung, Active-Recall-Coaching, Quiz-Generierung, Sokratisches Tutoring |
| **`04_system_architecture.md`** | Technische Architektur: Datenmodell, RAG-Pipeline, LLM-Stack, Speicherung, lokale vs. Cloud |
| **`05_ui_ux_design.md`** | UI-Design: Daily Flow, Screens, ASCII-Mockups, minimal aber komplett |
| **`06_implementation_roadmap.md`** | Phasenplan: MVP → V1 → V2, Milestones, Technologie-Wahl, was zuerst |

---

## Erwarteter Aufwand & Output (für dich, den Nutzer)

- **Setup pro Fach:** ~30 min Material hochladen, ~10 min Themenliste durchgehen.
- **Tägliches Lernen:** 60–120 min, hochkonzentriert.
- **Erwartetes Ergebnis:** In der Klausurphase keine Panik, keine Nachtsessions. Du gehst rein und weißt, du kannst es.

## Was das System *nicht* ist

- **Kein** Bullshit-Generator, der dir Folien zusammenfasst. Zusammenfassungen lesen ist passiv und ineffektiv.
- **Kein** ChatGPT-Wrapper, der Antworten ausspuckt. Das System lässt **dich** die Antwort produzieren.
- **Keine** Gamification mit Streaks und Punkten. Die Belohnung ist, dass du es kannst.

---

*Stand: 2026-05-08. Überarbeitung nach jedem absolvierten Klausurzyklus.*
