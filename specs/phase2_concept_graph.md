# Spec: Concept Graph Visualization

> Status: `implemented`
> Phase: 2
> Verwandte Research: [research/04_system_architecture.md](../research/04_system_architecture.md) · [research/05_ui_ux_design.md](../research/05_ui_ux_design.md)

## Ziel

Der User kann unter `/courses/[courseId]/graph` einen hierarchischen Abhängigkeitsgraphen aller Konzepte eines Kurses sehen — als Orientierungshilfe, welche Themen aufeinander aufbauen. Hover zeigt Details, Klick navigiert zur Review-Session.

## Nicht-Ziel

- Interaktives Bearbeiten von Edges (kein Drag & Drop, keine Edge-Creation im UI)
- Concept-spezifische gefilterte Review-Sessions
- Mobile-Layout
- Automatische Seed-Logik für `ConceptEdge` aus `prerequisites`-JSON (das ist Ingest-Scope)
- Gamification, Streaks, XP

## Akzeptanzkriterien

- [ ] `GET /api/courses/{courseId}/graph` gibt `{ nodes, edges }` zurück; 404 wenn Course nicht existiert
- [ ] Nur Concepts und Edges des angegebenen Kurses werden zurückgegeben (keine Cross-Course-Leaks)
- [ ] `/courses/[courseId]/graph` rendert einen React-Flow-Graphen mit dagre-Tree-Layout
- [ ] Jeder Node zeigt den Concept-Namen; Hover-Tooltip zeigt `summary` und `type`
- [ ] Klick auf einen Node navigiert zu `/courses/[courseId]/review`
- [ ] Kein Node vorhanden → leerer Zustand mit kurzer Meldung (kein Absturz)
- [ ] `pytest -m "not live"` bleibt grün, `npm test` + `npm run build` bleiben grün

## Datenmodell-Änderungen

Keine. `ConceptEdge` (composite PK: `src`, `dst`, `relation`) und `Concept` existieren bereits:

```sql
-- Bereits vorhanden:
CREATE TABLE concepts (
    id TEXT PRIMARY KEY, course_id TEXT, name TEXT, type TEXT,
    summary TEXT, target_bloom INTEGER, importance REAL,
    prerequisites JSON, source_pages JSON
);

CREATE TABLE concept_edges (
    src  TEXT REFERENCES concepts(id) ON DELETE CASCADE,
    dst  TEXT REFERENCES concepts(id),
    relation TEXT,
    PRIMARY KEY (src, dst, relation)
);
```

Keine neue Migration nötig.

## API-Änderungen

### `GET /api/courses/{courseId}/graph`

Neuer Endpoint im bestehenden `concepts`-Router (oder eigener `graph`-Router).

```
GET /api/courses/{courseId}/graph

Response 200:
{
  "nodes": [
    { "id": "uuid", "name": "SGD", "summary": "Stochastic Gradient Descent...", "type": "algorithm" }
  ],
  "edges": [
    { "src": "uuid-a", "dst": "uuid-b", "relation": "prerequisite" }
  ]
}

Response 404: { "detail": "Course not found" }
```

Logik:
1. Prüfe ob Course existiert → 404 falls nicht.
2. Lade alle Concepts mit `course_id == courseId`.
3. Lade alle ConceptEdges mit `src IN concept_ids AND dst IN concept_ids`.
4. Gib `ConceptGraphResponse` zurück (leere Listen wenn keine Concepts).

### Pydantic Schemas (`backend/app/api/schemas/graph.py`)

```python
class GraphNode(BaseModel):
    id: str
    name: str | None
    summary: str | None
    type: str | None

class GraphEdge(BaseModel):
    src: str
    dst: str
    relation: str

class ConceptGraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
```

## UI-Änderungen

### Neue npm-Pakete

- `@xyflow/react` — React Flow v12 (MIT, React-native, kein ESM-Problem mit Vitest wenn gemockt)
- `@dagrejs/dagre` — Hierarchisches Layout (MIT)

### Neue Dateien

- `frontend/app/courses/[courseId]/graph/page.tsx` — Server Component (delegiert an `<ConceptGraph>`)
- `frontend/components/ConceptGraph.tsx` — Client Component (`'use client'`)

### ASCII-Mock

```
┌─────────────────────────────────────────────────────────────┐
│  Concept Graph · Linear Algebra                   [← Zurück]│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│              ┌─────────┐                                    │
│              │ Vektoren │                                   │
│              └────┬────┘                                    │
│                   │ prerequisite                            │
│         ┌─────────┴──────────┐                              │
│         │                    │                              │
│    ┌────▼────┐         ┌─────▼─────┐                       │
│    │  Matrizen│         │ Linearkombi│                       │
│    └────┬────┘         └─────┬─────┘                       │
│         │                    │                              │
│         └─────────┬──────────┘                              │
│                   │                                         │
│           ┌───────▼──────┐                                  │
│           │ Eigenvektoren │  ← Hover: Tooltip mit Summary   │
│           └──────────────┘                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### ConceptGraph-Komponente (Verhalten)

- `useEffect` → `fetch('/api/courses/{courseId}/graph')` on mount
- dagre-Layout berechnen (client-seitig, einmalig nach Laden)
- React Flow `<ReactFlow nodes={...} edges={...} />` mit `fitView`
- Custom Node: Name als Label, Hover → CSS-Tooltip mit `summary` + `type`
- `onNodeClick` → `router.push('/courses/{courseId}/review')`
- Loading-State: "Lade Graph…" · Empty-State: "Keine Concepts gefunden."
- Kein Zoom-Control nötig (React Flow baut es automatisch ein, kann bleiben)

### Vitest-Hinweis

React Flow nutzt `ResizeObserver` — in jsdom nicht verfügbar. `ConceptGraph.tsx` wird in Tests via `vi.mock('@xyflow/react', ...)` gemockt; getestet wird nur die Fetch-Logik und das Rendering der Node-Namen über den Mock.

`vitest.config.ts` braucht keine Änderung wenn React Flow vollständig gemockt wird.

## LLM-Calls

Keine — reine Datenaggregation und Visualisierung.

## Tests

### Backend (`tests/test_graph.py`)

- `test_graph_course_not_found` — GET auf unbekanntem Course → 404
- `test_graph_empty_course` — Course ohne Concepts → 200 + `{ nodes: [], edges: [] }`
- `test_graph_returns_nodes_and_edges` — 2 Concepts + 1 Edge → nodes.length == 2, edges.length == 1
- `test_graph_excludes_other_courses` — Edge zwischen Concepts verschiedener Kurse nicht zurückgegeben
- `test_graph_edge_fields` — `src`, `dst`, `relation` korrekt

### Frontend (`tests/conceptGraph.test.tsx`)

Mock: `vi.mock('@xyflow/react', () => ({ ReactFlow: ({ nodes }) => <div>{nodes.map(n => <span key={n.id}>{n.data.label}</span>)}</div>, ... }))`

- `test_renders_loading_state` — zeigt "Lade Graph…" vor Fetch-Antwort
- `test_renders_node_names` — nach Fetch, Concept-Namen im DOM sichtbar
- `test_empty_state` — bei `{ nodes: [], edges: [] }` → leerer-Zustand-Text sichtbar
- `test_node_click_navigates` — Klick auf Node → `router.push` aufgerufen

## Offene Fragen

- Soll der Graph auch von einer Kurs-Übersichtsseite verlinkt sein, oder reicht direkter URL-Aufruf? (Nach diesem Semester reviewen.)
- Welche `relation`-Typen existieren in echten Daten? (Irrelevant für MVP — alle Edges werden gleich dargestellt.)
