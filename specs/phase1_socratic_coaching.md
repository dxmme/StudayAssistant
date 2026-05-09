# Spec: Sokratisches Coaching (Streaming-Chat mit RAG)

> Status: `draft`
> Phase: 1
> Verwandte Research: [research/01_learning_science.md](../research/01_learning_science.md) §Sokratik, [research/04_system_architecture.md](../research/04_system_architecture.md) §Pipelines.D, [research/06_implementation_roadmap.md](../research/06_implementation_roadmap.md) §Phase-1

## Ziel
User wählt einen Course + Konzept (aus Liste der `concepts`-Tabelle), öffnet `/coach/{course_id}/{concept_id}`. Backend startet eine `coaching_session`, lädt RAG-Kontext (Top-k Chunks zum Konzept), baut System-Prompt mit Sokratik-Regeln + Kontext, und streamt LLM-Antworten via Server-Sent-Events (SSE). Mehr-Turn-Chat. Sokrates-Regel: LLM gibt **niemals direkt Antworten**, nur Fragen, Hinweise, Gegenfragen. Coaching-Session über 10 Turns ohne Bug.

## Nicht-Ziel
- **Kein** Diagnostic-Schritt am Ende (Phase 2). Transkript wird gespeichert, mehr nicht.
- **Kein** Plan-Update-Trigger (Phase 2).
- **Keine** Audio/Voice-Eingabe (Phase 5).
- **Keine** strukturierten Coaching-Skills (z. B. „Diagnose-Modus", „Erklär-Modus") — ein generischer Sokrates-Prompt für alle Sessions.
- **Keine** mehr-User-Sessions parallel (single-user).
- **Keine** Persistenz pro Turn — Transkript wird beim Session-Ende geschrieben, oder optional bei jedem User-Turn ergänzt (siehe Akzeptanzkriterien).
- **Keine** Bewertung der User-Antworten (Mastery-Score-Update kommt in Phase 2 mit Diagnostic).

## Akzeptanzkriterien
- [ ] `POST /api/coaching/sessions` Body `{course_id, concept_id, target_bloom?: int}` startet eine Session:
  - Lädt Concept (404 falls nicht existent).
  - Lädt RAG-Kontext: `RAGService.search(course_id, concept.name + " " + concept.summary, k=5)` aus Spec 1.2.
  - Erzeugt `coaching_sessions`-Row (UUID-id, `transcript=""`, `diagnostic=null`, `started_at=now()`).
  - Response `201 {session_id, opening_question}`. **Opening-Question** ist der erste LLM-Output (siehe Streaming unten — beim Session-Start wird der erste Turn synchron gestreamt und der Volltext zurückgegeben, Frontend zeigt ihn dann progressiv im nachfolgenden SSE-Endpoint? — Vereinfachung: erster Turn ist normaler `/turn`-Aufruf nach Session-Erstellung. Siehe unten.)
- [ ] **Vereinfacht:** Session-Erstellung gibt nur `{session_id}` zurück. Frontend ruft direkt `POST /api/coaching/sessions/{id}/turn` mit `{user_message: ""}` (leerer String beim Opening) und konsumiert die SSE-Antwort.
- [ ] `POST /api/coaching/sessions/{id}/turn` mit Body `{user_message: str}`:
  - Lädt vorhandenen Transkript-Verlauf.
  - Baut Messages-Liste: `[{role: user, content: M_1}, {role: assistant, content: A_1}, ..., {role: user, content: user_message}]`.
  - System-Prompt (gecacht): Sokrates-Regeln (Andy Matuschak-Style + Hattie/Bloom-Hinweise) + Concept-Card („Du coachst zu: <name>, type: <type>, summary: <summary>") + RAG-Kontext (5 Snippets, jeweils mit Page-Marker).
  - Ruft `LLMGateway.complete_stream(...)` (neu — Streaming-Variante, siehe unten), tier=`default` (Sonnet).
  - Streamt SSE-Events `data: {"type": "delta", "text": "..."}` an den Client; Endevent `data: {"type": "done", "tokens_in": N, "tokens_out": M, "cache_read": K}`.
  - Nach `done`: hängt `\n\n[USER]: ...\n[ASSISTANT]: ...` an `coaching_sessions.transcript` an.
- [ ] `POST /api/coaching/sessions/{id}/end` markiert Session als beendet, setzt `duration_min = (now - started_at).total_seconds()/60`. Response `200 {session_id, duration_min, turn_count}`.
- [ ] `GET /api/coaching/sessions/{id}` liefert Session inkl. Transkript.
- [ ] **Sokrates-Regel** im System-Prompt explizit: „Beantworte die Frage NIE direkt. Stelle Gegenfragen, biete Pfade an, lass den User selbst formulieren. Nur wenn der User dreimal hintereinander stockt, gib einen schmalen Hinweis." Plus: „Mathematik in LaTeX (`$...$` oder `$$...$$`)."
- [ ] Prompt-Caching aktiv: System-Prompt + RAG-Kontext im selben Cache-Block. Im zweiten Turn `cache_read_input_tokens > 0` (live-Test).
- [ ] **Frontend:** Route `/coach/[courseId]/[conceptId]/page.tsx`. UI: Concept-Header oben, Chat-Verlauf, Eingabefeld unten (Textarea + Enter-zum-Senden, Shift-Enter für Newline). Streaming-Output erscheint Token-für-Token. Math wird live mit KaTeX rerendert (Best-effort: nach `done`-Event vollständig rerendern, während Streaming Plain-Text).
- [ ] Strukturiertes Logging pro Turn: `session_id`, `concept_id`, `turn_index`, `user_message_chars`, `assistant_message_chars`, `tokens_in`, `tokens_out`, `cache_read`, `latency_ms`.
- [ ] **10-Turn-Bug-Free-Test:** scripted (oder manuell, dokumentiert) — 10 Turns hintereinander, keine Crashes, Transkript korrekt akkumuliert, kein Token-Overflow (Sonnet 200k context reicht).

## Datenmodell-Änderungen
Tabelle `coaching_sessions` aus Phase 0 vorhanden. Anpassung:
- `started_at` aktuell ggf. `TEXT` — auf `DateTime` umstellen (Migration `0004_coaching_started_at_datetime.py`, falls nicht schon mit 0002/0003 mitgemacht).
- Optional: `last_assistant_message`-Spalte? — Nein, kann aus Transkript abgeleitet werden.

## API-Änderungen

```
POST /api/coaching/sessions
Body: {course_id, concept_id, target_bloom?}
Response: 201 {session_id, started_at}
        | 404 (concept oder course not found)

POST /api/coaching/sessions/{id}/turn
Body: {user_message: str}
Response: text/event-stream
  data: {"type":"delta","text":"..."}
  data: {"type":"delta","text":"..."}
  ...
  data: {"type":"done","tokens_in":N,"tokens_out":M,"cache_read":K}

POST /api/coaching/sessions/{id}/end
Response: 200 {session_id, duration_min, turn_count}

GET /api/coaching/sessions/{id}
Response: 200 {id, course_id, concept_id, transcript, started_at, duration_min, diagnostic}

GET /api/courses/{course_id}/coaching/sessions
Response: 200 [{id, concept_id, started_at, duration_min}, ...]
```

## UI-Änderungen

ASCII-Mock:
```
┌──────────────────────────────────────────────────────────┐
│ Coaching · SVD                                  10 Turns │
├──────────────────────────────────────────────────────────┤
│ [A] Beginnen wir mit der Definition: Welche Eigenschaft  │
│     unterscheidet die Singulärwertzerlegung von der      │
│     Eigenwertzerlegung deiner Meinung nach?              │
│                                                          │
│ [U] Eigenwertzerlegung geht nur für quadratische ...     │
│                                                          │
│ [A] Genau. Und welche Konsequenz hat das für ...         │
│                                                          │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ Schreibe deine Antwort ...                          ↵│ │
│ └──────────────────────────────────────────────────────┘ │
│                                            [Ende-Knopf]  │
└──────────────────────────────────────────────────────────┘
```

Komponenten in `frontend/components/`:
- `CoachingSession.tsx` — orchestriert SSE-Stream, hält Verlauf.
- `ChatTurn.tsx` — rendert einen Turn (User oder Assistant), nutzt `MarkdownMath` aus Spec 1.4.
- `ChatInput.tsx` — Textarea, Enter zum Senden.

## LLM-Calls
- **Modell:** Sonnet (default-tier).
- **Prompt-Caching:** ja, auf `system`-Block (Sokrates-Regeln + Concept-Card + RAG-Kontext, ~3-4k Tokens).
- **Streaming:** ja. **Neue Methode** `LLMGateway.complete_stream(...) -> AsyncIterator[StreamEvent]` mit Events `delta(text)` und `done(usage)`. Nutzt das Anthropic-SDK-Streaming (`client.messages.stream(...)`).
- **Erwartete Tokens pro Turn:**
  - System ~3k (gecacht ab Turn 2)
  - History (kumulativ): Turn 1 = ~50, Turn 10 = ~3-5k
  - Output: 200-500
- **Retry:** bei `overloaded_error` 3 Retries (gleiche Logik wie `complete()`).

## Bibliotheken / Dependencies (neu)
- Backend: keine neue, `anthropic` SDK kann bereits streamen.
- Frontend: keine neue, native `EventSource` oder `fetch` mit `ReadableStream` für SSE — `EventSource` reicht.

## Tests
- Unit Backend (`tests/test_coaching_api.py`):
  - POST-Session-Create mit Mock-`RAGService` und Mock-`LLMGateway` → `coaching_sessions`-Row existiert.
  - POST-Turn-Endpoint mit Mock-Stream-Generator → SSE-Events werden korrekt emittiert (Test mit `httpx.AsyncClient`-Streaming).
  - End-Endpoint setzt `duration_min` korrekt.
- Integration Backend (`tests/test_coaching_live.py`, `@pytest.mark.live`):
  - Echter `RAGService` (mit Mock-Embeddings, da kein OpenAI-Key garantiert) und echter Anthropic-Call.
  - 2-Turn-Session: Turn 2 zeigt `cache_read_input_tokens > 0`.
- Frontend (`frontend/tests/CoachingSession.test.tsx`):
  - Mock-EventSource. Sende User-Message, simuliere `delta`-Events → UI zeigt Tokens progressiv.
  - `done`-Event triggert vollständigen Math-Rerender.
- Manuell dokumentiert: 10-Turn-Lauf gegen lokales SVD-Konzept → Screenshot in `docs/phase1_coaching_demo.md`.

## Offene Fragen
- **`complete_stream` als neue Methode neben `complete`:** ja, separate API. Beide nutzen die gleiche Routing/Caching-Logik, der einzige Unterschied ist `client.messages.stream` vs. `client.messages.create`. Refactor in `LLMGateway` ist klein.
- **SSE vs. WebSocket:** SSE reicht (uni-direktional Server→Client für Streaming, separater POST für User-Input). Phase 1 ohne WebSocket-Setup-Komplexität.
- **Konzept-Liste vor Coaching-Start:** UX-Frage. In dieser Spec wird der `concept_id` als URL-Param erwartet → Vorab-Auswahl auf `/courses/{id}/concepts`-Seite (simple Liste, gehört zu Spec 1.2). Falls 1.2 keine UI hat: Concept-Picker als Mini-Komponente hier rein — aber dann muss Backend-Endpoint `GET /api/courses/{id}/concepts` aus 1.2 da sein.
- **Offline / Anthropic-Down:** Keine Fallback-LLM in Phase 1. UI zeigt Error-Toast, Session bleibt offen.
- **Cache-TTL:** Default 5min. Wenn ein Turn länger als 5min dauert (User denkt nach), nächster Turn = Cache-Miss. Akzeptabel für Phase 1; Phase 2 ggf. auf 1h-Cache.
- **Wiederaufnahme einer alten Session?** — Nein, in Phase 1 ist eine Session = ein Aufruf. Beim erneuten Öffnen einer alten `session_id` wird Verlauf angezeigt, aber kein neuer Turn möglich, wenn `duration_min != null` (= beendet).
