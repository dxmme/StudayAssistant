# Spec: Worked Examples (Phase 3.1)

> Status: `draft`
> Phase: 3
> Verwandte Research: [research/06_implementation_roadmap.md](../research/06_implementation_roadmap.md) · [research/01_learning_science.md](../research/01_learning_science.md)

## Ziel

Der User sieht nach einer Karten-Bewertung (oder auf Abruf) eine vollständige, schritt-für-schritt Lösungsskizze mit Erklärungen — generiert vom LLM auf Basis der Kartenfrage und der RAG-Chunks des zugehörigen Materials.

## Nicht-Ziel

- Kein Persistent-Storage der generierten Beispiele (kein DB-Eintrag, kein JSON-Array auf der Card)
- Kein "Faded Worked Example" (Stage-Übergänge, partielle Lücken) — das ist Phase 4+
- Kein Auto-Trigger beim App-Start oder Laden der Review-Session
- Kein Streamen in der Antwort (ganzer Block auf einmal; kein SSE)
- Keine Coding-Sandbox (Phase 4)
- Kein Rating des Worked Example durch den User (kein Feedback-Loop auf die Generierung)

## Akzeptanzkriterien

- [ ] In der ReviewSession gibt es nach dem Aufdecken der Antwort einen Button "Lösung anzeigen"
- [ ] Klick öffnet ein Modal mit Spinner; nach LLM-Antwort wird das Worked Example in Markdown+KaTeX gerendert
- [ ] Der Button ist unabhängig vom Rating sichtbar (User kann jederzeit Lösung abrufen, nicht nur nach 1-2)
- [ ] `POST /api/cards/{card_id}/worked-example` gibt `{ "content": "<markdown>" }` zurück (200)
- [ ] Antwort ist nicht persistiert — jeder Aufruf generiert neu
- [ ] LLM-Call nutzt RAG-Kontext der Karte (via `rag_search.py`) — Top-3 Chunks aus dem zugehörigen Material
- [ ] Tier: `hard` (claude-opus-4-7) für mathematisch schwierige Karten
- [ ] Strukturiertes Output-Format: Preamble → Schritte → Key Insight (siehe Prompt-Spezifikation)
- [ ] Modal schließbar via ×-Button und Escape-Taste
- [ ] `pytest -m "not live"` grün (127+ passed), `npm test` + `npm run build` grün

## Datenmodell-Änderungen

**Keine.** Worked Examples werden nicht persistiert.

## API-Änderungen

### `POST /api/cards/{card_id}/worked-example`

Generiert ein Worked Example für die gegebene Karte. Kein Request-Body nötig.

```
POST /api/cards/{card_id}/worked-example

Response 200:
{
  "content": "## Worked Example\n\n**Problem:** ...\n\n**Lösung:**\n1. ...\n\n**Key Insight:** ..."
}

Response 404: { "detail": "Card not found" }
```

**Generierungslogik:**
1. Lade `Card` mit `concept_id` → `Concept` → `course_id` → Material-Verknüpfung
2. Hole RAG-Kontext: `rag_search(card.question, course_id, top_k=3)` → 3 Chunks
3. Baue System-Prompt (gecacht, ephemeral):
   ```
   Du bist ein Lernassistent für ML-Master-Studenten.
   Erstelle ein vollständiges Worked Example für die folgende Aufgabe.
   Kontext aus dem Kursmaterial:
   {rag_chunks}

   Format (Markdown + LaTeX):
   ## Worked Example
   **Problem:** [Frage nochmal klar formuliert]

   **Lösung:**
   [Schritt-für-Schritt, jeder Schritt nummeriert, Mathe in LaTeX]

   **Key Insight:** [1-2 Sätze — warum funktioniert das so?]
   ```
4. User-Message: `Aufgabe: {card.question}\n\nAntwort laut Karte: {card.answer}`
5. `LLMGateway.complete(system_block, messages, tier="hard")`
6. Gib `{ "content": response_text }` zurück

**Neue Datei:** `backend/app/api/worked_examples.py` (Router mit Prefix `/api/cards`)

### Pydantic-Schema

```python
class WorkedExampleResponse(BaseModel):
    content: str
```

## UI-Änderungen

### Änderung in `ReviewSession.tsx`

Nach dem Aufdecken der Antwort (State `revealed = true`): Button "Lösung anzeigen" erscheint unterhalb der Rating-Buttons.

```
┌────────────────────────────────────────────────────────┐
│  Frage: Was ist die VC-Dimension des Halbraums in R^d? │
│  ──────────────────────────────────────────────────────│
│  Antwort: d+1                                          │
│                                                        │
│  [ 1 Again ] [ 2 Hard ] [ 3 Good ] [ 4 Easy ]         │
│                                                        │
│  [ Lösung anzeigen ]   ← neuer Button                 │
└────────────────────────────────────────────────────────┘
```

Klick → `WorkedExampleModal` öffnet sich.

### Neue Komponente `WorkedExampleModal.tsx`

```
┌─────────────────────────────────────────────────────────────┐
│  Worked Example                                         [×] │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  [Spinner während Laden]                                    │
│                                                             │
│  ## Worked Example                                          │
│  **Problem:** Was ist die VC-Dimension des Halbraums...     │
│                                                             │
│  **Lösung:**                                                │
│  1. Wir suchen die größte Menge S ⊂ ℝᵈ die shattert...    │
│  2. ...                                                     │
│                                                             │
│  **Key Insight:** Die d+1 Freiheitsgrade entsprechen...     │
│                                                             │
│  [ Schließen ]                                              │
└─────────────────────────────────────────────────────────────┘
```

- Inhalt via `MarkdownMath` (KaTeX) gerendert
- ESC und ×-Button schließen das Modal
- Kein Rating des Worked Example — nur lesen

### Keine neue Route

`WorkedExampleModal` ist eine Komponente innerhalb der bestehenden `/review`-Route.

## LLM-Calls

| Eigenschaft | Wert |
|---|---|
| Tier | `hard` (claude-opus-4-7) |
| Prompt-Caching | System-Block als `list[dict]` mit `cache_control: ephemeral` |
| RAG | Top-3 Chunks aus `rag_search` |
| Erwartete Input-Tokens | ~800–1500 (System + RAG + Card) |
| Erwartete Output-Tokens | ~400–800 (Markdown-Lösung) |
| Streaming | Nein — ein synchrones `complete()` |

## Tests

### Backend (`backend/tests/test_worked_examples.py`)

- `test_worked_example_returns_content` — POST für existierende Card → 200, `content` ist nicht-leerer String
- `test_worked_example_card_not_found` — POST für unbekannte Card-ID → 404
- `test_worked_example_calls_llm_with_rag` — Mock `rag_search` + `LLMGateway.complete`; verify beide aufgerufen mit richtigen Args
- `test_worked_example_uses_hard_tier` — Mock-Spy auf Gateway; verify `tier="hard"` übergeben

### Frontend (`frontend/tests/worked-example.test.tsx`)

- `test_button_hidden_before_reveal` — vor Aufdecken: "Lösung anzeigen" nicht sichtbar
- `test_button_visible_after_reveal` — nach Aufdecken: Button im DOM
- `test_modal_opens_on_click` — Klick → Modal sichtbar, fetch aufgerufen
- `test_modal_shows_spinner` — während Laden: Spinner sichtbar
- `test_modal_renders_content` — gemockter fetch → Markdown-Inhalt gerendert
- `test_modal_closes_on_escape` — ESC-Taste → Modal geschlossen
- `test_modal_closes_on_x` — ×-Klick → Modal geschlossen

## Offene Fragen

- Falls RAG-Kontext leer (Material noch nicht ingested): Worked Example ohne Kontext generieren oder Fehler zurückgeben? → Annahme: ohne RAG generieren, Qualität sinkt aber kein Error.
- Soll der Button auch in der `/review/multi`-Route auftauchen? → Annahme: erstmal nur in Single-Card-Review; Multi-Review ist eigene Route.
