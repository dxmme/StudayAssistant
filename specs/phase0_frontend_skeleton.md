# Spec: Frontend Skeleton (Next.js + Tailwind + KaTeX)

> Status: `draft`
> Phase: 0
> Verwandte Research: [research/05_ui_ux_design.md](../research/05_ui_ux_design.md)

## Ziel
Next.js (App Router) startet via `pnpm dev`, Root-Page rendert Tailwind-styled Layout mit einer KaTeX-gerenderten Beispielformel. TypeScript strict.

## Nicht-Ziel
- Keine echten Komponenten aus `research/05` (Card-Review, Coaching, Quiz). Nur Hello-World.
- Keine API-Anbindung (kein Aufruf des Backends).
- Keine Routen außer `/`.
- Kein State-Management-Setup (TanStack Query / Zustand kommen in Phase 1).

## Akzeptanzkriterien
- [ ] `pnpm install` erfolgreich.
- [ ] `pnpm dev` startet Next.js auf `:3000` ohne Build-Fehler.
- [ ] `tsconfig.json` hat `"strict": true`, `"noUncheckedIndexedAccess": true`.
- [ ] `app/layout.tsx` lädt globale Tailwind-CSS und KaTeX-CSS.
- [ ] `app/page.tsx` rendert: Titel „StudyAssistant", Subtitel „Phase 0 — Skeleton", einen Tailwind-styled Container, und die Formel `e^{i\pi} + 1 = 0` via KaTeX (server-side gerendert).
- [ ] Beim Build (`pnpm build`) keine Type-Errors, keine ESLint-Errors.
- [ ] `pnpm test` (Vitest) grün: ein Smoke-Test rendert `<HomePage />` und prüft, dass Titel + Formel-Container im DOM sind.

## Datenmodell-Änderungen
Keine.

## API-Änderungen
Keine.

## UI-Änderungen
**Eine Page (`/`):** vertikal zentrierter Container, max-width 720px, Tailwind-typografie, KaTeX-Rendering der Test-Formel.

```
+-----------------------------------+
|  StudyAssistant                   |
|  Phase 0 — Skeleton               |
|                                   |
|       e^{iπ} + 1 = 0              |
|                                   |
+-----------------------------------+
```

Keine Navigation, kein Header, kein Footer.

## Verzeichnisstruktur
```
frontend/
  app/
    layout.tsx           # Root layout, lädt globals.css + katex.min.css
    page.tsx             # / (HomePage mit Test-Formel)
    globals.css          # Tailwind directives
  components/
    Math.tsx             # <Math tex="..." /> Wrapper um KaTeX (server-rendered)
  tests/
    home.test.tsx        # Vitest smoke test
  next.config.mjs
  tailwind.config.ts
  postcss.config.js
  tsconfig.json
  package.json
  vitest.config.ts
```

## LLM-Calls
Keine.

## Tests
- Vitest:
  - `home.test.tsx`: `render(<HomePage />)`; assert getByText('StudyAssistant'); assert document enthält `.katex` element.
- Manuell: `pnpm dev`, im Browser auf `:3000` Formel sichtbar (visueller Smoke-Test).

## Offene Fragen
- KaTeX server-side via `katex.renderToString` oder client-side via `react-katex`? — Server-side: schneller, kein Hydration-Mismatch, `<Math>`-Komponente ruft `renderToString` und gibt `dangerouslySetInnerHTML` zurück.
- Tailwind v3 oder v4? — v3, weil v4 (alpha/beta) noch instabil und Plugin-Ökosystem hängt hinterher.
