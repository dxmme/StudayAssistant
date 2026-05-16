# Spec: Coaching-Refinement — Sokratik, dynamische Länge, Abschluss

> Status: `draft`
> Phase: 3
> Verwandte Research: [research/01_learning_science.md](../research/01_learning_science.md)
> Baut auf: [specs/phase3_learn_mode.md](phase3_learn_mode.md) (Coaching war dort „unverändert")

## Ziel

Die Coaching-Session vom reinen Frage-Antwort-Chat zu einem didaktisch geschlossenen
Lernbaustein machen. Vier Verbesserungen:

1. **Sokratik schärfen** — der Student artikuliert sein Verständnis zuerst; Fehlannahmen
   bleiben aber **nie unkorrigiert** stehen. Nach echtem Versuch gibt es konkrete
   Korrektur + die präzise Definition.
2. **Dynamische Länge** — keine feste Turn-Zahl. Neue Konzepte: in die Tiefe, bis der
   Kern sitzt. Reviews: kurz und gezielt. Wenn der Coach den Kern als verstanden
   einschätzt, gibt er ein maschinenlesbares Signal — das Frontend hebt dann den
   „Ende"-Button hervor („Konzept verstanden — Session beenden?").
3. **Abschluss-Summary** — ein KI-generiertes Fazit beim Session-Ende: Kernidee,
   präzise Definition, was behandelt wurde.
4. **Mini-Quiz** — ein kleiner Verständnis-Check (2–4 Multiple-Choice-Fragen) auf die
   Core-Concepts. Rein diagnostisch.

Motivation: ~65 Tage bis zur Klausur. Jedes Konzept muss **einmal richtig** verstanden
werden, ohne Zeit zu verschwenden. Der Coach trifft das Optimum aus Tiefe und Tempo.

## Nicht-Ziel

- Persistente Quiz-Bank, Adaptive Quiz-Difficulty, FSRS-Einfluss durch Quiz-Antworten
- Coaching-Diagnostik (Skill-Schätzung) — eigenes Feature, spätere Phase
- Multi-Session-Coaching (Verlauf über mehrere Sessions hinweg)
- Automatisches Beenden der Session (Coach *empfiehlt*, der User klickt „Ende")
- Mobile-Layout · Gamification

## Designentscheidungen (aus `/grill-me`)

| Frage | Entscheidung |
|---|---|
| Summary persistent? | Ja — `CoachingSession.summary` (Text). Einmal generiert, nie neu (Token-Spar). |
| Quiz persistent? | Ja — `CoachingSession.quiz` (JSON). Frage-Set, kein User-Answer-Tracking. |
| Stage-Übergang | `end_session` setzt `stage → coached` — unabhängig vom Generierungs-Erfolg. |
| Eigene Quiz-Tabelle? | Nein — JSON-Spalte auf `CoachingSession` (YAGNI). |
| Endpoint-Struktur | All-in-one: `POST .../end` macht **einen** LLM-Call (Summary+Quiz gemeinsam, geteilter Transcript-Kontext = token-effizient), persistiert beides, gibt beides zurück. |
| Quiz → FSRS? | Nein. Rein diagnostisch. User-Antworten werden nicht gespeichert. |
| LLM-Tier | `default` für Summary+Quiz-Generierung. |
| Prompt-Caching am Ende | Nein — einmaliger Call pro Session. |
| Frontend-Phasen | Linear: `idle/streaming → concluding → summary → quiz → complete`. |
| Quiz-Format | Multiple Choice, variable Anzahl 2–4 (LLM entscheidet nach Konzept-Komplexität), Core-fokussiert, kurz beantwortbar. |
| Keyboard-Nav | Ja — Zahlentasten `1`–`4` für MC-Optionen (Konsistenz mit Review-Session). |
| LaTeX | `MarkdownMath` überall in Summary + Quiz (Formeln sind lernrelevant). |
| Kurze Session (1–2 Turns) | Summary+Quiz trotzdem generieren. Bei 0 Turns: überspringen. |
| Generierungs-Fehler | `/end` gibt `200` mit `summary: null, quiz: []`; Frontend zeigt Fehler + „Weiter". |
| Skip | Summary- und Quiz-Screen sind überspringbar (User kennt es schon). |

## Datenmodell-Änderungen

Eine Migration: zwei Spalten auf `coaching_sessions`.

```python
# models/coaching.py — neue Felder
summary: Mapped[Optional[str]] = mapped_column(Text)
quiz: Mapped[Optional[Any]] = mapped_column(JSON)
```

```
ALTER TABLE coaching_sessions ADD COLUMN summary TEXT;
ALTER TABLE coaching_sessions ADD COLUMN quiz JSON;
```

Migration mit `render_as_batch=True`. Bestehende Sessions: beide `NULL`.
`diagnostic` bleibt ungenutzt (kein Quiz-Answer-Tracking).

## Quiz-Datenstruktur (JSON)

```json
{
  "quiz": [
    {
      "question": "Was charakterisiert ... ?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_index": 1,
      "explanation": "B ist korrekt, weil ..."
    }
  ]
}
```

- 2–4 Fragen, je 3–4 Optionen.
- `correct_index`: 0-basiert.
- `explanation`: kurze Begründung, wird nach Antwort angezeigt.

## Slices

### Slice A — Sokratik schärfen + dynamische Länge

`coaching_prompt.py`:

- `build_system_prompt(concept, hits, mode)` — neuer Parameter `mode: Literal["deep", "review"]`.
- `coaching.py` (`turn`-Endpoint) leitet `mode` aus `concept.stage` ab:
  `new`/`explained` → `"deep"`, sonst → `"review"`.
- `SOCRATIC_RULES` überarbeiten:
  - **Student zuerst** — er artikuliert sein Verständnis, bevor er Input bekommt (bleibt).
  - **Misconception-Regel** — keine Fehlannahme bleibt stehen. Nach echtem Versuch
    (oder 2 Stalls): konkrete Korrektur + **präzise, korrekte Definition** geben,
    danach mit einer Frage gegenprüfen. (Lockert die alte „NIE die Antwort"-Härte —
    bei 65 Tagen bis zur Klausur sind hängengebliebene Fehldefinitionen schädlich.)
  - **Core-Fokus** — den *einen* Kern des Konzepts früh identifizieren, jede Frage
    darauf hinsteuern; Randdetails sekundär.
  - **Dynamische Länge** — `deep`: in die Tiefe bis der Kern wirklich sitzt.
    `review`: kurz, wenige gezielte Checks.
  - **Korrekte Definition vor Abschluss** — der Student soll die präzise Definition
    einmal gehört/wiederholt haben, bevor der Coach zum Beenden rät.
  - **Bereit-Signal** — sobald der Student den Kern nachweislich versteht *und* die
    korrekte Definition gehört hat, hängt der Coach als **allerletzte Zeile** den
    Sentinel `[[READY]]` an (eigene Zeile). Reines Maschinen-Signal — nie erklären,
    nie sonst verwenden.

**Turn-Endpoint — Sentinel-Handling.** Der `event_generator` puffert den Stream so,
dass die letzten `len("[[READY]]")` Zeichen zurückgehalten werden, bevor sie als
`delta` rausgehen. Bei Stream-Ende: prüfen, ob `full_response` (getrimmt) auf den
Sentinel endet → `ready = True`, Sentinel aus dem Text strippen, Rest flushen.
Das `done`-SSE-Event trägt zusätzlich `ready: bool`. Der Sentinel landet **nie** im
sichtbaren Text und **nie** im persistierten Transcript (`append_turn` bekommt den
bereinigten Text).

### Slice B — Summary + Quiz-Generierung (Backend)

Neue Datei `services/coaching_summary.py`:

```python
def generate_conclusion(
    concept: Concept, transcript: str, hits: list[ChunkHit], llm: LLMGateway
) -> tuple[str | None, list[dict]]:
    """Ein LLM-Call (tier=default, JSON-Output): erzeugt Summary + 2–4 MC-Fragen.
    Bei leerem Transcript oder LLM-Fehler: (None, [])."""
```

`POST /api/coaching/sessions/{session_id}/end` erweitern:
- Dependencies `llm` + `rag` ergänzen.
- Nach `duration_min`-Berechnung: `stage → coached` setzen (wie bisher, **vor**
  der Generierung — Fehler beim Generieren darf den Stage-Übergang nicht verhindern).
- Bei Transcript mit ≥1 Turn: `generate_conclusion(...)` aufrufen, RAG-gegroundet.
- `summary` + `quiz` auf der Session persistieren, `commit`.
- Response erweitern.

`schemas/coaching.py` — `CoachingSessionEnded` erweitern:
```python
class QuizQuestion(BaseModel):
    question: str
    options: list[str]
    correct_index: int
    explanation: str

class CoachingSessionEnded(BaseModel):
    session_id: str
    duration_min: float
    turn_count: int
    summary: str | None
    quiz: list[QuizQuestion]
```
`CoachingSessionResponse` ebenfalls um `summary` + `quiz` erweitern.

### Slice C — Abschluss-Flow (Frontend)

`CoachingSession.tsx` — `Phase` erweitern:
`'creating' | 'opening' | 'idle' | 'streaming' | 'concluding' | 'summary' | 'quiz' | 'complete' | 'error'`

- `SSEStreamEvent` um `ready?: boolean` erweitern. Empfängt das `done`-Event
  `ready: true`, wird ein State `coachReady` gesetzt → der „Ende"-Button wird
  hervorgehoben (Accent-Hintergrund) und zeigt einen Hinweis
  „Konzept verstanden — Session beenden?".
- „Ende"-Klick → `concluding` (Ladezustand), ruft `/end`, erhält `summary` + `quiz`.
- `summary` vorhanden → Phase `summary`. Sonst (Fehler/leer) → Fehlerhinweis + direkt
  zu `complete`.
- `summary`-Screen: `CoachingSummary` rendern, Buttons „Zum Quiz" / „Überspringen".
- Quiz vorhanden → Phase `quiz`, sonst direkt `complete`.
- `quiz`-Screen: `CoachingQuiz`, Buttons „Überspringen" möglich.
- `complete` → `onEnd?.()` feuert (löst Card-Generierung in `LearnSession` aus).

Neue Komponenten:
- `CoachingSummary.tsx` — zeigt Summary via `MarkdownMath`.
- `CoachingQuiz.tsx` — MC-Quiz: Frage + Optionen, Auswahl per Klick **oder Taste 1–4**,
  zeigt nach Antwort korrekt/falsch + `explanation`, „Weiter" zur nächsten Frage.
  Letzte Frage → Abschluss. Antworten rein lokal (kein Persist, kein FSRS).
  Alle Textfelder via `MarkdownMath` (LaTeX).

`LearnSession.tsx` — `CoachStep`: `onEnd` der `CoachingSession` feuert jetzt erst bei
`complete` (nach Summary+Quiz). Card-Generierung + „Weiter"-Button bleiben an `onEnd`
gekoppelt — funktioniert unverändert, nur der Zeitpunkt verschiebt sich ans Flow-Ende.

## API-Vertrag

```
POST /api/coaching/sessions/{session_id}/end
Response 200 {
  "session_id": str,
  "duration_min": float,
  "turn_count": int,
  "summary": str | null,
  "quiz": [
    { "question": str, "options": [str], "correct_index": int, "explanation": str }
  ]
}
404 — Session nicht gefunden
```

Bei Generierungs-Fehler: weiterhin `200`, `summary: null`, `quiz: []`.

```
POST /api/coaching/sessions/{session_id}/turn  (SSE, unverändert bis auf:)
done-Event:  { "type": "done", "tokens_in": int, "tokens_out": int,
               "cache_read": int, "ready": bool }
```

## Akzeptanzkriterien

### Slice A
- [ ] `build_system_prompt` akzeptiert `mode`; `deep`/`review` erzeugen sichtbar
      unterschiedliche Längen-/Tiefen-Anweisungen im Prompt
- [ ] `turn`-Endpoint leitet `mode` korrekt aus `concept.stage` ab
- [ ] Prompt enthält explizit: Misconception-Korrektur, Core-Fokus, korrekte Definition
      vor Abschluss, `[[READY]]`-Sentinel-Anweisung
- [ ] Sentinel wird aus Stream-Text **und** Transcript gestrippt; `done`-Event
      trägt korrektes `ready`-Flag (true nur wenn Antwort auf Sentinel endet)

### Slice B
- [ ] Migration fügt `summary` + `quiz` hinzu (`render_as_batch=True`)
- [ ] `generate_conclusion` mit gemocktem Gateway → Summary-String + 2–4 valide
      MC-Fragen (`correct_index` im Options-Bereich)
- [ ] leeres Transcript → `(None, [])`, kein LLM-Call
- [ ] LLM-Fehler → `(None, [])`, kein Crash
- [ ] `/end` persistiert `summary` + `quiz`, gibt sie zurück
- [ ] `stage → coached` auch wenn Generierung fehlschlägt
- [ ] `/end` bei unbekannter Session → 404

### Slice C
- [ ] `done`-Event mit `ready: true` → „Ende"-Button hervorgehoben + Hinweis-Text
- [ ] „Ende" → Ladezustand → Summary-Screen
- [ ] Summary rendert LaTeX korrekt (`MarkdownMath`)
- [ ] Quiz: Auswahl per Klick und per Taste `1`–`4`; Feedback + `explanation` nach Antwort
- [ ] „Überspringen" auf Summary- und Quiz-Screen springt zu `complete`
- [ ] Generierungs-Fehler (`summary: null`) → Fehlerhinweis, Flow läuft weiter
- [ ] `onEnd` feuert erst bei `complete` → Card-Generierung im Learn-Mode unverändert
- [ ] `pytest -m "not live"` grün · `npm test` + `npm run build` grün

## Tests

### Backend (`tests/test_coaching_*.py`)
- `build_system_prompt(mode="deep" | "review")` → unterschiedlicher Prompt-Inhalt
- Turn-Stream: Antwort mit `[[READY]]` am Ende → Sentinel nicht im Delta-Text,
  nicht im Transcript, `done`-Event hat `ready: true`; ohne Sentinel → `ready: false`
- `generate_conclusion`: gemocktes Gateway → erwartete Struktur; leeres Transcript → `(None, [])`;
  Gateway wirft → `(None, [])`
- `/end`: Response enthält `summary` + `quiz`; Session-Felder persistiert;
  `stage` wird `coached` (auch bei Generierungs-Fehler); 404 bei unbekannter Session
- bestehende Coaching-Tests bleiben grün (`test_coaching_api.py`)

### Frontend (`tests/CoachingSession.test.tsx`)
- „Ende"-Klick → `/end` gemockt → Summary-Screen erscheint
- Quiz: Tastendruck `1` wählt erste Option; Feedback sichtbar
- „Überspringen" überspringt zu `complete`/`onEnd`
- `summary: null` → Fehlerhinweis, kein Crash

## Offene Punkte
- `CoachingQuiz` ist MC-Self-Check; das bestehende `QuizCard.tsx` (Freitext, LLM-gegradet)
  bleibt davon unberührt — zwei verschiedene Quiz-Arten, bewusst getrennt.
