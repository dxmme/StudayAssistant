# 02 — ML Master Tübingen: Was hier *anders* gelernt werden muss

> Generische Lerntipps reichen nicht. ML-Master-Inhalte haben spezifische Eigenschaften — viel Mathematik, formale Beweise, hochabstrakte Konzepte mit überraschend wichtiger geometrischer Intuition. Dieses Dokument schneidet die in `01_learning_science.md` etablierten Prinzipien auf **dein** Studium zu.

---

## Curriculum-Kontext (Tübingen ML M.Sc.)

### Pflicht (24 ECTS)

- **Deep Learning** (Geiger, Hennig)
- **Statistical Machine Learning** (von Luxburg)
- **Probabilistic Machine Learning** (Hennig)

### Häufig belegte Wahlpflicht

- Mathematics for Machine Learning
- Data Literacy
- Probabilistic Inference and Learning
- Computer Vision (Geiger)
- Robotics
- Reinforcement Learning
- NLP
- Causality (Schölkopf)
- Kernel Methods (Schölkopf)
- Probabilistic Numerics (Hennig)
- Robustness, Adversarial ML (Hein)
- Self-Driving Cars
- Time Series, Neural Data Analysis, Efficient ML in Hardware

### Was das für die Vorbereitung bedeutet

- **Sehr unterschiedliche Klausurformate** je Lehrstuhl (Hennig: stark proof-orientiert + Bayesian; von Luxburg: sehr klar definierte Konzeptfragen + theoretische Bounds; Geiger: anwendungsnah + Architektur-Verständnis).
- **Altklausuren sind Gold.** Prüfungsstil ist pro Dozent extrem konsistent.

---

## Die 6 Inhaltstypen — und wie man jeden lernt

| Typ | Beispiel | Lernmodus |
| --- | --- | --- |
| **Definitionen** | Was ist eine RKHS? | Karteikarte (cloze + Erklären in eigenen Worten) |
| **Sätze + Voraussetzungen** | Mercer's Theorem, Representer Theorem | Karteikarte (Aussage) + Karteikarte (Voraussetzungen) + Karteikarte (Konsequenz/Beispiel) |
| **Beweise** | Konvergenzbeweis SGD | Stufenweise: Beweisstruktur → Schlüssel-Schritt → eigene Rekonstruktion |
| **Algorithmen** | EM, k-Means, Adam | Pseudocode-Karte + „warum jeder Schritt" + Mini-Implementation |
| **Mathematische Manipulationen** | Dichten transformieren, Erwartungswerte vereinfachen | Worked Examples → Faded → frei |
| **Konzeptuelle Intuition** | Bias-Variance, Overfitting, Geometrie der SVD | Diagramme + Erklären-Lassen vom LLM |

---

## 1. Definitionen lernen

### Falsch

> *„Eine RKHS ist ein Hilbertraum von Funktionen, in dem die Auswertungs-Funktional stetig ist."* → auswendig.

### Richtig (3 Karten pro Definition)

```
Karte A — Definition
  Front: Was ist eine RKHS?
  Back:  Hilbertraum H von Funktionen f: X → ℝ, in dem für jedes x ∈ X
         das Auswertungsfunktional δ_x(f) = f(x) stetig ist.
         (äquivalent: ∃ Kernel k mit Reproducing Property f(x) = ⟨f, k(·,x)⟩)

Karte B — Intuition
  Front: Warum braucht man stetige Auswertung?
  Back:  Wenn f_n → f in H-Norm, soll auch f_n(x) → f(x) gelten —
         sonst ist „nahe in H" nicht „nahe punktweise". Erlaubt
         Generalisierung von endlichdim. linearer Algebra auf Funktionen.

Karte C — Beispiel + Gegenbeispiel
  Front: L²([0,1]) — RKHS oder nicht?
  Back:  NICHT. Punkt-Auswertung ist auf L² nicht definiert
         (Funktionen sind nur bis auf Nullmengen festgelegt).
```

→ Eine Definition ohne Intuition + Beispiel = nicht gelernt.

---

## 2. Sätze + Voraussetzungen

Hier ist die Forschungsempfehlung **„elaborative interrogation"** zentral:

```
Karte: Representer Theorem
  Front: Aussage des Representer-Theorems?
  Back:  Lösung eines regularisierten Empirical-Risk-Problems
         über RKHS hat Form f* = Σ α_i k(·, x_i).

Folge-Karte (warum):
  Front: Warum gilt das Representer-Theorem?
  Back:  Jede Komponente von f orthogonal zu span{k(·, x_i)} 
         beeinflusst den Loss nicht (k(·, x_i) reproduziert),
         erhöht aber den Regularizer-Term ‖f‖². → Optimum 
         liegt in span{k(·, x_i)}.

Folge-Karte (Voraussetzungen):
  Front: Welche Annahmen braucht das Representer-Theorem?
  Back:  Loss als Funktion von (y_i, f(x_i)), 
         monoton wachsende Regularisierung in ‖f‖_H.

Folge-Karte (Konsequenz):
  Front: Warum macht das Representer-Theorem Kernel-Lernen praktisch möglich?
  Back:  Reduziert ∞-dim. Optimierungsproblem auf n-dim.
         (n = Trainingsdatengröße). → Kernel-Trick.
```

→ Vier Karten pro Satz, nicht eine.

---

## 3. Beweise lernen

Beweise auswendig = Lernzeitverschwendung. Aber Beweise *verstehen* ist absolut prüfungsrelevant in Tübingen.

### Methode: 3-Stufen-Beweisstruktur

```
Stufe 1 — Beweisskelett (1 Karte)
  Front: Wie strukturiert sich der Beweis von Mercer's Theorem?
  Back:  (1) Operator T_k auf L² ist kompakt, selbstadjungiert, positiv.
         (2) Spektralsatz → orthonormale Eigenbasis {φ_i}, EW λ_i ≥ 0.
         (3) Konvergenz der Reihe k(x,y) = Σ λ_i φ_i(x) φ_i(y).

Stufe 2 — Schlüsselschritt(e) als eigene Karten
  Front: Warum ist T_k positiv?
  Back:  ⟨T_k f, f⟩ = ∫∫ k(x,y) f(x) f(y) dx dy ≥ 0
         folgt direkt aus PSD-Definition von k.

Stufe 3 — Rekonstruktion
  Aufgabe: „Beweise Mercer's Theorem auf einem Blatt, ohne Hilfsmittel."
  Selbstcheck: Stimmt mit dem Skript-Beweis überein?
```

→ Im System: Beweis-Karten haben einen *Reconstruction-Mode*: Du tippst/sprichst den Beweis, das LLM vergleicht Schritt für Schritt mit der hinterlegten Korrektur und zeigt dir, wo du eine Voraussetzung oder einen Schritt vergessen hast.

---

## 4. Algorithmen verinnerlichen

```
Karte 1 — Pseudocode
  Front: Pseudocode des EM-Algorithmus?
  Back:  Initialize θ⁽⁰⁾
         repeat:
           E-step: q(z) = p(z | x, θ⁽ᵗ⁾)
           M-step: θ⁽ᵗ⁺¹⁾ = argmax_θ E_q[log p(x, z | θ)]
         until convergence

Karte 2 — Warum jeder Schritt
  Front: Was passiert mathematisch beim E-Step?
  Back:  Untere Schranke ELBO an log p(x|θ) wird durch die exakte 
         Posterior q*(z) = p(z|x,θ) tight gemacht.

Karte 3 — Garantien & Fallstricke
  Front: Wann konvergiert EM gegen das globale Maximum?
  Back:  Im Allgemeinen NICHT. Nur lokale Konvergenz garantiert.
         Mehrere Restarts nötig.

Karte 4 — Mini-Implementation
  Aufgabe: Implementiere EM für GMM in 30 Zeilen NumPy.
```

→ Algorithmen *müssen* einmal selbst implementiert werden. Theoretisches Verständnis ohne Hands-on bricht in der Klausur, sobald nach „was passiert, wenn …" gefragt wird.

---

## 5. Mathematische Manipulationen

Beispiel: Posterior für Gauss × Gauss herleiten. Klassische Klausuraufgabe.

### Methode: Worked → Faded → Free

```
Stufe 1 — Worked Example (vollständig vorgemacht)
  „Hier ist die komplette Herleitung Schritt für Schritt mit Kommentaren."

Stufe 2 — Faded
  „Hier sind die Schritte 1, 2, 5, 6. Fülle 3 und 4 selbst."

Stufe 3 — Free
  „Leite die Posterior her, gegeben Prior N(μ_0, σ_0²) und Likelihood N(x; μ, σ²)."
```

→ Übergang erfolgt anhand FSRS-Stability. Sobald eine Stufe „leicht" wird (Stability > 30d), nächste Stufe.

---

## 6. Konzeptuelle Intuition (das Tübingen-Spezifikum)

Schölkopf, Hennig & von Luxburg fragen oft *„Erkläre intuitiv, warum …"*. Reines Formalwissen reicht nicht.

### Methode: Multi-Modal + Sokratisch

Beispiel-Konzept: **Bias-Variance Tradeoff**

```
1. Visuell: Plot mit drei Kurven (Bias², Variance, Total Error vs. Modellkomplexität).
2. Formal: E[(y - f̂)²] = Bias² + Variance + σ²_Noise.
3. Sokratisches Dialog mit LLM-Coach:
   Coach: Warum sinkt Bias mit Modellkomplexität?
   Du:   Weil ein größeres Modell näher an die wahre Funktion approximieren kann.
   Coach: Genau. Was passiert mit Variance?
   Du:   Steigt — das Modell passt sich an Rauschen an.
   Coach: Welche Annahme über Daten brauchst du implizit?
   Du:   ...?
   Coach: Tipp: i.i.d.
   Du:   Ah — wenn die Daten nicht i.i.d. sind, ist Variance über Resampling 
         nicht mehr aussagekräftig...
4. Anwenden: Quizfrage mit konkretem Szenario.
```

---

## Pro Modul: Strategie-Cheat-Sheet

| Modul | Schwerpunkt | Lerntechnik | Wieviel Beweis-Reconstruction? |
| --- | --- | --- | --- |
| **Statistical ML** (von Luxburg) | Theoreme, Bounds, klare Konzepte | Definition-Trio + Sätze mit allen 4 Karten | Hoch |
| **Probabilistic ML** (Hennig) | Ableitungen, Bayesian, Numerik | Worked → Faded → Free + Konzept-Karten | Mittel-Hoch |
| **Deep Learning** (Geiger) | Architekturen, Mechanismen, anwendbar | Diagramme + Mini-Implementations + Algorithmus-Karten | Mittel |
| **Mathematics for ML** | Lineare Algebra, Calculus, Probability | Drill (viele Berechnungs-Karten) + Geometrische Intuition | Niedrig |
| **Computer Vision** | Pipelines, Architekturen, klassisch + DL | Diagramme + Vergleichs-Karten („wann X, wann Y") | Niedrig |
| **Causality** | Konzepte, do-Kalkül, Beweise | Definitionen-Trio + viele Beispiel-Karten | Hoch |
| **Kernel Methods** | RKHS-Theorie + Algorithmen | Definitionen-Trio + Theoreme + Worked Examples | Hoch |

---

## Klausurvorbereitungs-Phasen

### Phase 1 — Semesterbegleitend (Woche 1 bis vor der Phase)

- **Pro Vorlesungswoche:** Karten anlegen (Definitionen, Sätze, Beweise) + 1 Worked Example durchgehen + 1 Übungszettel-Aufgabe selbst lösen.
- **Tägliches Reviewen** der fälligen Karten (FSRS).

### Phase 2 — Klausurvorbereitung (6–8 Wochen vor der Klausur)

- **Strukturiert:** Pro Vorlesungswoche 1–2 Tage „Recall + Verstehen + Quiz".
- Konzept-Maps pro Modul: Wie hängen die Themen zusammen?
- **Erste Altklausur** ohne Notizen, ohne Zeitdruck — diagnostisch.
- Lücken → werden zu neuen Karten.

### Phase 3 — Mock-Exam-Phase (letzte 2–3 Wochen)

- **Vollständige Altklausur** unter realen Klausurbedingungen (Zeit, Tools, ggf. Cheat-Sheet).
- Auswertung: jede falsch/halb-richtige Aufgabe → Karten + Worked Example + Re-Quiz.
- **Cornell 5-Day Plan** in der letzten Woche pro Klausur:
  - Tag 5: Material überblicken, Karten reviewen
  - Tag 4: Schwächste 30 % vertiefen
  - Tag 3: Mock Exam
  - Tag 2: Lücken schließen
  - Tag 1: leichtes Reviewen, früh schlafen

### Phase 4 — Tag der Klausur

- Nur **leichtes Karten-Review** am Vormittag, nicht mehr neu lernen.
- Vertrauen ist der Modus, nicht Cramming.

---

## Sonderfälle, die das System beherrschen muss

### Beweise mit LaTeX-Reconstruction

Du tippst den Beweis in LaTeX (oder sprichst ihn). Das LLM:
1. Parst die mathematischen Schritte.
2. Vergleicht mit der Soll-Lösung.
3. Identifiziert: fehlender Schritt? Falsche Implikation? Vorsetzung vergessen?
4. Stellt Sokratische Rückfrage statt Korrektur zu zeigen.

### Numerik / Hands-on

Bestimmte Konzepte (Gradient Descent, Sampling-Methoden) erfordern *Code*. Das System bietet pro Konzept einen **Mini-Coding-Prompt** (z. B. „Implementiere Metropolis-Hastings für eine 2D-Gauß-Posterior in 25 Zeilen") + automatische Auswertung (Python-Sandbox).

### Cheat-Sheet-Generierung

In manchen Tübinger Klausuren ist ein einseitiges Cheat-Sheet erlaubt. Das System erstellt am Ende der Phase 3 ein **kondensiertes Cheat-Sheet** aus deinen schwächsten Karten + den von dir markierten Schlüsselformeln — als LaTeX-Vorlage.

---

## Anti-Pattern: Was du *nicht* tun sollst

- ❌ Folien noch zwei Mal durchlesen → null Effekt.
- ❌ Nur „leichte" Karten reviewen → Illusion von Fortschritt.
- ❌ Beweise auswendig lernen, ohne sie zu rekonstruieren.
- ❌ Übungszettel anschauen, ohne sie selbst zu rechnen.
- ❌ Spät anfangen + cramen → Variance hoch, Mittelwert niedrig.
- ❌ ChatGPT die Lösungen ausspucken lassen → keine Generation, kein Lernen.

---

*Stand: 2026-05-08. Wird pro Modul verfeinert, sobald erste Erfahrungswerte vorliegen.*
