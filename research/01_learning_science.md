# 01 — Learning Science: Was die Forschung über optimales Lernen sagt

> Diese Datei ist die *Begründung* für jede Designentscheidung im System.
> Wenn jemand fragt „warum macht ihr Quiz statt Zusammenfassungen?" — die Antwort steht hier.

---

## TL;DR — Die 7 Hebel mit der größten Evidenz

| Technik | Effect Size | Quelle | Im System verwendet als |
| --- | --- | --- | --- |
| **Retrieval Practice (Active Recall)** | g ≈ 0.50–0.61 | Rowland 2014, Adesope 2017 | Karteikarten, freies Erklären, Quiz |
| **Spaced/Distributed Practice** | hoch (Top-2 in Dunlosky) | Donoghue & Hattie 2021 (242 Studien, 169.000 Probanden) | FSRS-Scheduling |
| **Interleaving** | moderat | Dunlosky 2013 | Mischung aus mehreren Themen pro Session |
| **Worked Examples** | sehr hoch (Anfänger) | Sweller & Cooper | Erste Begegnung mit neuem Konzept |
| **Self-Explanation / Elaborative Interrogation** | moderat | Dunlosky 2013 | LLM-Coach lässt dich Konzepte erklären |
| **Dual Coding** | +89% Test-Score (Mayer 2009) | Paivio, Mayer | Diagramme + Text in Karten |
| **Practice Testing unter Klausurbedingungen** | hoch | div. | Mock-Exam-Phase |

---

## 1. Retrieval Practice — der Königsweg

### Was ist das?

> Sich Information aus dem Gedächtnis *aktiv abrufen*, statt sie passiv wiederzulesen.

Beispiel: Statt das Skript zur SVD nochmal zu lesen — Buch zu, Blatt nehmen, aufschreiben: *"Was ist die SVD? Wofür braucht man sie? Wie hängt sie mit Eigenwerten zusammen?"*. Erst dann nachschlagen.

### Warum funktioniert es?

- **Testing Effect:** Jeder Abruf-Versuch *modifiziert* die Erinnerungsspur, statt sie nur zu reaktivieren. Erfolgreicher Abruf macht zukünftige Abrufe leichter (Bjork: *retrieval strength* ↑).
- **Generation Effect:** Selbst generierte Antworten werden besser behalten als gelesene.
- **Diagnostic Effect:** Du merkst sofort, was du nicht kannst — bevor es in der Klausur peinlich wird.

### Evidenz

- **Rowland (2014):** g = 0.50 (Retrieval vs. Wiederlesen)
- **Adesope et al. (2017):** g = 0.61 (Retrieval vs. alle anderen Techniken)
- **Donoghue & Hattie (2021):** Practice Testing unter den **zwei effektivsten** Techniken überhaupt.

### Implementierung im System

- **Karteikarten** (FSRS-geschedult).
- **Free-Recall-Sessions:** Vor dem LLM frei über ein Thema sprechen, das LLM identifiziert Lücken.
- **Quiz** mit unterschiedlichen Bloom-Levels.
- Niemals nur "lies das nochmal".

---

## 2. Spaced Repetition / Distributed Practice

### Kernprinzip

> *"Eine Stunde pro Tag über 20 Tage > 10 Stunden pro Tag an 2 Tagen."*

Das Vergessen folgt der **Ebbinghaus-Kurve** (exponentieller Zerfall). Jede Wiederholung **flacht** die Kurve ab — und zwar umso mehr, je näher am Punkt des Vergessens sie passiert.

### Optimale Intervalle

- **Faustregel:** Spacing-Intervall ≈ 10 % der Ziel-Retention-Dauer.
  *Klausur in 100 Tagen → optimaler Abstand zwischen Reviews ~10 Tage.*
- **Expanding Intervals:** Erst kurze Abstände (1d, 3d), dann immer länger (7d, 14d, 30d, 90d).
- Das macht **FSRS** (siehe `03_techniques_and_tools.md`) automatisch — basierend auf einem ML-Modell, das auf 700M Anki-Reviews trainiert wurde.

### Warum funktioniert es?

- **Forgetting-Effort-Hypothesis (Bjork):** Wenn man sich an etwas *fast nicht mehr* erinnern kann und es dann doch abruft, wird die Spur am stärksten gefestigt.
- **Konsolidierung:** Gedächtnis-Konsolidierung läuft über Schlaf/Tage, nicht über Stunden.

### Konsequenz fürs System

- Lernen ist **kontinuierlich, nicht episodisch**. Lieber 60 min/Tag über 12 Wochen als 8 h/Tag in Woche 12.
- **Klausur-Termin** ist ein harter Eingabe-Parameter für den Scheduler.

---

## 3. Interleaving (Mischen verschiedener Themen)

### Was ist es?

Statt **Block-Practice** (Thema A → A → A → A → B → B → B → B) wird gemischt: A → B → C → A → C → B.

### Warum?

- Du musst **erkennen**, *welches* Werkzeug für ein Problem zuständig ist — genau die Skill, die in einer Klausur verlangt wird.
- Block-Practice fühlt sich besser an *(„ich kann's!")*, aber die Performance bricht zusammen, sobald die Probleme gemischt kommen.
- **Desirable Difficulty** (Bjork): Kurzfristig mehr Anstrengung, langfristig deutlich besserer Transfer.

### Caveat

- **Innerhalb eines Konzepts** zuerst Block-Practice bis Grundverständnis steht — *dann* Interleaving. Sonst Cognitive Overload.
- Effekte stärker bei *ähnlichen* Konzepten (z. B. verschiedene Wahrscheinlichkeitsverteilungen) als bei völlig disparaten.

### Im System

- Quiz-Engine zieht Fragen aus den letzten *N* Themen, nicht nur dem heutigen.
- Karteikarten werden über alle Themen eines Fachs gemischt.

---

## 4. Cognitive Load Theory (Sweller)

> Das Arbeitsgedächtnis ist klein (~4 Chunks). Lerndesign muss diese Limitation respektieren.

### Drei Arten von Cognitive Load

1. **Intrinsic** — die Schwierigkeit des Stoffs selbst. (SVD ist intrinsisch komplex.)
2. **Extraneous** — *unnötige* kognitive Belastung durch schlechtes Design (zerstreute Diagramme, schlechter Aufbau).
3. **Germane** — *produktive* kognitive Belastung beim Schemabilden.

**Ziel:** Extraneous minimieren, Germane maximieren, Intrinsic durch *chunking* in verdauliche Häppchen brechen.

### Worked Examples (für Anfänger)

- Erste Begegnung mit neuem Stoff: **vollständig durchgerechnetes Beispiel** anschauen, nicht selbst lösen.
- Sweller & Cooper: Worked-Example-Lerner schlagen Problem-Solving-Lerner deutlich.
- Schrittweiser Übergang: vollständig gelöst → teilweise gelöst → komplett selbst lösen.

### Expertise Reversal Effect

- Was für Anfänger funktioniert, **schadet** Fortgeschrittenen (Redundanz!).
- → Das System muss erkennen, *wo du stehst*, und Schwierigkeit hochziehen.
- → FSRS-Stability + Quiz-Performance als Indikator.

### Im System

- **Anfangs:** viele Worked Examples, geführte Schritte.
- **Mittel:** Faded Examples (einige Schritte fehlen), Self-Explanation.
- **Fortgeschritten:** freies Problemlösen, Klausuraufgaben.

---

## 5. Self-Explanation & Elaborative Interrogation

### Self-Explanation

> *„Was bedeutet dieser Schritt? Warum gilt das?"* — du erklärst **dir selbst** während des Lernens.

### Elaborative Interrogation

> *„Warum ist das so?"* — du fragst nach Begründungen statt nur Fakten zu speichern.

### Warum funktioniert es?

- Erzwingt **tiefes Verarbeiten** statt oberflächliches Erkennen.
- Baut **Verbindungen** zu Vorwissen.
- Deckt **Wissenslücken** auf — das LLM kann hier wie ein Sokrates wirken.

### Im System (Killer-Feature)

Der **Active-Recall-LLM**:

```
USER: Erklär mir, warum SVD numerisch stabiler ist als Eigenzerlegung.
LLM:  Geh durch deine Argumentation. Was passiert mit der Konditionszahl?
USER: [erklärt halbherzig, lässt Detail weg]
LLM:  Du sagst "weil's symmetrisch ist". Aber A^T A ist immer symmetrisch — 
      wo genau kommt die Stabilität her? Was ist mit κ(A^T A) vs κ(A)?
USER: Ach ja, die Konditionszahl quadriert sich bei A^T A...
LLM:  Genau. Und welche Konsequenz hat das für SVD?
```

→ Das LLM **gibt nie die Antwort**. Es legt nur den Finger in die Lücke.

---

## 6. Desirable Difficulties (Bjork)

> Lernbedingungen, die *kurzfristig* Performance senken, aber *langfristig* Retention und Transfer steigern.

### Die fünf Bjork-Hebel

1. **Spacing** (siehe oben)
2. **Interleaving** (siehe oben)
3. **Testing** (siehe oben)
4. **Variation** der Aufgaben & Kontexte (verschiedene Beispieltypen)
5. **Reduzierte Feedback-Frequenz** (nicht nach jedem Schritt korrigieren)

### Performance ≠ Lernen

Das ist die zentrale Einsicht. Jemand, der sich beim Üben *leicht* fühlt, hat sich oft **nicht** verbessert. Anstrengung beim Abruf = Hirn arbeitet = Lernen passiert.

### Konsequenz für UX

- **Keine** „Du machst das großartig!"-Belohnungen für leichte Aufgaben.
- Das System *darf* sich hart anfühlen.
- Klare Kommunikation: *„Wenn du dich anstrengst, lernst du. Wenn alles flutscht, bist du auf zu leichtem Niveau."*

---

## 7. Dual Coding Theory (Paivio, Mayer)

> Information, die **visuell** *und* **verbal** kodiert wird, hat zwei Anker — und wird tiefer behalten.

### Evidenz

- Mayer 2009: Multimedia-Lernen mit Dual Coding → +89 % Test-Score.
- Butcher 2006: Diagramme mit Text → +0.48 SD im Verstehen.

### Anwendung auf ML-Mathematik

ML *ist* visuell (Geometrie der SVD, Vektorräume, Optimierungslandschaften, Bayes-Netze). Aber die meisten Studierenden lernen nur die Formeln.

### Im System

- Karteikarten enthalten — wo möglich — **Diagramm + Formel + verbale Erklärung**.
- Karten ohne visuelles Element für visuelle Konzepte werden als „incomplete" geflaggt.
- Concept-Maps pro Fach, die Verbindungen zwischen Themen explizit machen.

---

## 8. Bloom-Taxonomie — Tiefe der Verarbeitung

```
Erinnern   →  Verstehen  →  Anwenden  →  Analysieren  →  Bewerten  →  Erschaffen
(remember)    (understand)   (apply)       (analyze)       (evaluate)    (create)
```

### Warum wichtig fürs System?

- **Klausuren** verlangen meist Levels 3–5 (anwenden, analysieren, bewerten).
- **Schlechtes Lernen** bleibt auf Level 1 hängen (auswendig).
- → Wir analysieren **Altklausuren** und klassifizieren *jede* Frage nach Bloom-Level. Das ist der Ziel-Level für jedes Konzept.

### Beispiel ML

| Konzept: Backpropagation | Bloom-Level | Frage-Beispiel |
| --- | --- | --- |
| Definition | Remember | „Was ist Backprop?" |
| Mechanik | Understand | „Erkläre die Kettenregel-Anwendung" |
| Anwendung | Apply | „Berechne die Gradienten für dieses Netz" |
| Diagnose | Analyze | „Warum stagniert hier der Gradient?" |
| Vergleich | Evaluate | „Wann ist Backprop ineffizient vs. vorzuziehen?" |
| Variation | Create | „Entwirf eine alternative Update-Regel" |

→ Karteikarten und Quizfragen werden über alle Levels verteilt, mit Schwerpunkt auf den klausurrelevanten.

---

## 9. Was *nicht* funktioniert (laut Dunlosky 2013)

| Technik | Utility | Warum schwach |
| --- | --- | --- |
| **Highlighting / Underlining** | low | passiv, keine Verarbeitung |
| **Re-Reading** | low | Vertrautheit ≠ Wissen |
| **Summarization** (für die meisten) | low–moderate | hängt extrem von Skill ab |
| **Imagery for Text** | low | nur Text-spezifisch |
| **Keyword Mnemonics** | low | nur für Vokabeln nützlich |

→ **Konsequenz:** Das System bietet diese Techniken **nicht** als Standard-Workflow an. (Notizen sind ok als *Nebenprodukt* des Verarbeitens, nicht als Lernmodus.)

---

## 10. Synthese: Wie alles zusammenwirkt

```
                ┌──────────────────────────┐
                │   Material + Altklausur  │
                └────────────┬─────────────┘
                             │
                  Bloom-Klassifikation
                  Konzept-Extraktion
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
   Worked Examples     Karteikarten        Quizfragen
   (Anfangsphase)      (FSRS-Spacing)      (Interleaved,
          │                  │              alle Bloom-Levels)
          ▼                  ▼                  ▼
   Self-Explanation    Active Recall      Practice Testing
   mit LLM-Coach       (verbal + visuell)  (Mock Exams am Ende)
          │                  │                  │
          └──────────────────┼──────────────────┘
                             ▼
                  Wissens-Diagnose
                  (Lücken → Plan-Update)
                             │
                             ▼
                  Klausur — vorbereitet.
```

---

## Quellen / Weiterführend

- **Dunlosky, J. et al. (2013).** Improving Students' Learning With Effective Learning Techniques. *Psychological Science in the Public Interest, 14(1), 4–58.*
- **Rowland, C. A. (2014).** The effect of testing versus restudy on retention: A meta-analytic review of the testing effect. *Psychological Bulletin.*
- **Adesope, O. O. et al. (2017).** Rethinking the use of tests: A meta-analysis of practice testing. *Review of Educational Research.*
- **Donoghue, G. M., & Hattie, J. A. C. (2021).** A meta-analysis of ten learning techniques.
- **Bjork, E. L., & Bjork, R. A. (2011).** Making things hard on yourself, but in a good way. *Psychology and the Real World.*
- **Sweller, J., van Merrienboer, J., & Paas, F. (1998).** Cognitive architecture and instructional design.
- **Mayer, R. E. (2009).** Multimedia Learning (2nd ed.). Cambridge University Press.
- **Paivio, A. (1986).** Mental Representations: A Dual Coding Approach.
- **Anderson, L. W. & Krathwohl, D. R. (2001).** A Taxonomy for Learning, Teaching, and Assessing (Bloom Revised).
- **Matuschak, A. & Nielsen, M.** *Quantum Country* — Experiment im Mnemonic Medium. https://quantum.country
- **Matuschak, A.** *How to write good prompts.* https://andymatuschak.org/prompts
