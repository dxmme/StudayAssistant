# Spec: Daily-Review-UI (Front/Back, Tastatur 1-4)

> Status: `draft`
> Phase: 1
> Verwandte Research: [research/05_ui_ux_design.md](../research/05_ui_ux_design.md) §Review-Mode, [research/06_implementation_roadmap.md](../research/06_implementation_roadmap.md) §Phase-1

## Ziel
User öffnet `/review/{course_id}`, sieht Karte für Karte (Front zuerst), drückt **Space** zum Umdrehen, **1-4** zur Bewertung. Markdown + LaTeX (KaTeX) gerendert auf Front und Back. Nach jeder Bewertung lädt die nächste fällige Karte. Wenn keine Karte mehr fällig: „Du bist fertig für heute." Plus Stats: heute reviewed, davon lapsed, durchschnittlich Rating. Vollständig per Tastatur bedienbar — kein einziger Mausklick nötig nach Seitenaufruf.

## Nicht-Ziel
- Kein Karten-Erstellungs-UI in dieser Spec — User legt Karten via API/Curl/Postman an (oder über simples Form-UI als Add-On falls nötig, dann minimal). Reines Reviewen hier.
- Keine Inline-Bearbeitung beim Review.
- Keine Cram-Mode/Learn-Ahead — nur „heute fällig".
- Keine Animationen / Card-Flip-Effekte. Sofortiges Umblenden reicht.
- Keine Bilder, keine Audio-Anhänge.
- Keine Multi-Course-Kombination — pro Aufruf ein Course.

## Akzeptanzkriterien
- [ ] Route `/review/[courseId]/page.tsx` (Next.js App Router).
- [ ] Beim Mount: `GET /api/courses/{courseId}/cards/due` → wenn leer, sofort Empty-State.
- [ ] State-Maschine pro Karte:
  - `front` (default beim Laden einer Karte) — zeigt nur `card.front`.
  - `back` (nach Space) — zeigt `card.front` + `card.back`.
  - Im `front`-State: nur Space funktioniert.
  - Im `back`-State: 1, 2, 3, 4 → POST `/api/cards/{id}/review`, dann nächste Karte oder Empty-State.
- [ ] Rating-Mapping ist im UI sichtbar (Footer-Leiste): `1 Again | 2 Hard | 3 Good | 4 Easy`. Tasten-Hinweis als Caption darunter klein.
- [ ] Markdown-Rendering: `react-markdown` + `rehype-katex` + `remark-math` (für KaTeX-Inline `$...$` und Display `$$...$$`). Bestehende `Math.tsx`-Komponente weiter nutzen für rohe LaTeX-Strings.
- [ ] Zähler oben: `X von Y`, wobei `Y` initial die Anzahl der fälligen Karten beim Mount ist und sich nicht ändert (auch bei Lapses, die den Pool theoretisch erweitern könnten — Phase 1: 1 Pass).
- [ ] Bei Netzwerkfehler beim Review-POST: Error-Toast, Karte bleibt im `back`-State, Rating-Tasten erneut nutzbar (Idempotenz: gleicher Request schickt 2 reviews — akzeptabel für Phase 1, siehe Offene Fragen).
- [ ] Empty-State: Heading „Heute fertig", Stats (Anzahl reviewed in dieser Session, davon `rating==1` als „Lapses").
- [ ] Vollständige Tastaturbedienung verifiziert: Cypress/Playwright-Test simuliert nur Keyboard-Events durch eine 5-Karten-Session.
- [ ] Mobile? — siehe research/05: Phase 1 = Desktop-only. Layout `min-w-[640px]`, kein Mobile-Tuning.
- [ ] Responsive Card-Container: max-width `48rem`, Center, ausreichend Padding für lange Inhalte (Math-Display darf `overflow-x-auto`).

## Datenmodell-Änderungen
Keine.

## API-Änderungen
Keine — nutzt `GET /api/courses/{course_id}/cards/due` und `POST /api/cards/{id}/review` aus Spec 1.3.

## UI-Änderungen

ASCII-Mock:
```
┌──────────────────────────────────────────────────────────┐
│ Statistical Machine Learning · Review              3/12  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│   Was ist die SVD einer Matrix A ∈ R^{m×n}?              │
│                                                          │
│   [Front-State: nur diese Zeile sichtbar]                │
│                                                          │
├──────────────────────────────────────────────────────────┤
│                  [Space] umdrehen                        │
└──────────────────────────────────────────────────────────┘

nach Space:

┌──────────────────────────────────────────────────────────┐
│ Statistical Machine Learning · Review              3/12  │
├──────────────────────────────────────────────────────────┤
│   Front:  Was ist die SVD von A ∈ R^{m×n}?               │
│   ────────────────────────────────────────────────       │
│   Back:   A = U Σ Vᵀ   mit U,V orthogonal,               │
│          Σ Diagonalmatrix mit Singulärwerten ≥ 0         │
├──────────────────────────────────────────────────────────┤
│   [1] Again   [2] Hard   [3] Good   [4] Easy             │
└──────────────────────────────────────────────────────────┘
```

Komponenten in `frontend/components/`:
- `ReviewSession.tsx` — orchestriert die Session, hält State `cards[]`, `currentIndex`, `flipped`, `stats`.
- `CardView.tsx` — Front/Back-Render, nutzt `MarkdownMath.tsx`.
- `MarkdownMath.tsx` — wrapper um `react-markdown` mit Math-Plugins.
- `RatingBar.tsx` — Footer mit Tasten-Hinweis.

## LLM-Calls
Keine.

## Bibliotheken / Dependencies (neu, Frontend)
- `react-markdown`
- `remark-math`
- `rehype-katex`

(`katex` selbst ist bereits in Phase 0 für die `Math.tsx`-Komponente eingebunden.)

## Tests
- Unit (Vitest, `frontend/tests/ReviewSession.test.tsx`):
  - Mock `fetch`. Lade 3 Karten. Drücke Space → `back`-State sichtbar. Drücke `3` → `POST /api/cards/{id}/review` mit `rating: 3`, nächste Karte erscheint im `front`-State.
  - Letzte Karte bewerten → Empty-State sichtbar mit korrekten Stats.
- Unit (`frontend/tests/MarkdownMath.test.tsx`):
  - String mit Inline `$x^2$` → `<span class="katex">` im DOM.
  - Display-Math `$$\sum_i x_i$$` → entsprechender KaTeX-Display-Render.
- E2E (Playwright, `frontend/tests-e2e/review.spec.ts`):
  - Backend hochfahren mit 3 Karten Fixture, Frontend hochfahren, `/review/{id}` öffnen, Tastatursequenz Space-3-Space-3-Space-3 → Empty-State.
  - **Nur** Keyboard-Events, keine Mausklicks.

## Offene Fragen
- **Idempotenz für Review-POST:** Bei Doppelklick / Doppel-Tastendruck schickt der Client zwei Requests. Phase-1-Lösung: Frontend setzt `requestInFlight=true` und ignoriert weitere Tastendrücke bis Response da. Reicht das? — Ja, simpel. Server-side Idempotenz (Idempotency-Key) erst bei Multi-User.
- **Lange Karten:** Was, wenn `back` 5 Bildschirme lang ist (z. B. ein Beweis)? — Scrollbar im Card-Container; Tastendrücke 1-4 wirken trotzdem, da auf `window` gebunden.
- **Was tun, wenn neue Karte mitten in Session due wird (z. B. Lapse einer früher reviewten Karte mit re-due in 1 min)?** — Phase 1 ignoriert das; der Pool ist beim Mount fix. User kann nach Empty-State `/review/...` neu öffnen.
- **Empty-State, wenn von Anfang an leer:** Heading „Keine Karten fällig" + Link zu `/courses/{id}/cards` (Karten-Listen-UI — gibt es noch nicht in Phase 1, also als 404-Link akzeptabel oder einfach Text ohne Link).
- **Add-Card-Form?** Optional Mini-Form auf `/courses/{id}/cards` mit `front`-`back`-Textareas — falls dieser Spec zu eng wird, in Spec 1.4b separieren. Default: drin lassen, minimaler Form, kein Markdown-Preview.
