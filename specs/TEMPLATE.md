# Spec: <Feature-Name>

> Status: `draft` | `approved` | `implemented`
> Phase: 0 / 1 / 2 / 3 / 4 / 5
> Verwandte Research: [research/04_system_architecture.md](../research/04_system_architecture.md)

## Ziel
Ein Satz, was am Ende möglich ist. Aus User-Sicht.

## Nicht-Ziel
Was bewusst ausgelassen wird. Schützt vor Scope-Creep.

## Akzeptanzkriterien
- [ ] Konkretes Verhalten 1 (testbar)
- [ ] Konkretes Verhalten 2
- [ ] ...

## Datenmodell-Änderungen
Tabellen / Felder / Migrations.

```sql
-- z.B. ALTER TABLE cards ADD COLUMN ...
```

## API-Änderungen
Endpoints, Schemas, Status-Codes.

```
POST /api/cards
Request:  { ... }
Response: 201 { ... }
```

## UI-Änderungen
Welche Screens, welche Komponenten. ASCII-Mock optional.

## LLM-Calls (falls relevant)
- Modell: Sonnet / Haiku / Opus
- Prompt-Caching: ja/nein, was wird gecached
- Erwartete Tokens pro Call

## Tests
- Unit: ...
- Integration: ...
- e2e: ...

## Offene Fragen
- ?
