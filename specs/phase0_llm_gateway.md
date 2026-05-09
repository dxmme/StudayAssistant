# Spec: LLM-Gateway (Anthropic + Prompt-Caching + Model-Routing)

> Status: `draft`
> Phase: 0
> Verwandte Research: [research/04_system_architecture.md](../research/04_system_architecture.md)

## Ziel
Ein `LLMGateway`-Service kapselt Anthropic-Calls, unterstützt Model-Routing (Sonnet/Haiku/Opus), aktiviert Prompt-Caching auf System-Prompt + RAG-Kontext, loggt Token-Verbrauch. Ein Test-Coaching-Flow zeigt im zweiten Call `cache_read_input_tokens > 0`.

## Nicht-Ziel
- Kein Streaming (kommt in Phase 1, wenn Coaching-UI gebaut wird).
- Kein RAG-Retrieval — die Kontext-Strings werden für den Test hardcoded gemockt (echtes RAG erst in Phase 1).
- Keine Cost-Tracking-DB-Tabelle. Logs reichen.
- Kein Multi-Provider — nur Anthropic.
- Keine Tool-Use / Function-Calling.

## Akzeptanzkriterien
- [ ] `backend/app/services/llm_gateway.py` enthält Klasse `LLMGateway` mit Methode:
  ```python
  def complete(
      self,
      system: str,
      messages: list[Message],
      tier: Literal["default", "cheap", "hard"] = "default",
      cache_breakpoints: list[CacheBreakpoint] | None = None,
      max_tokens: int = 1024,
  ) -> LLMResponse
  ```
- [ ] Model-Routing: `default` → `claude-sonnet-4-6`, `cheap` → `claude-haiku-4-5-20251001`, `hard` → `claude-opus-4-7`. Tier-IDs zentral in `app/services/llm_models.py`.
- [ ] Prompt-Caching aktiv: `system`-Block bekommt automatisch `cache_control: {"type": "ephemeral"}`. Optionale weitere Breakpoints (z. B. RAG-Kontext) per `cache_breakpoints`-Argument.
- [ ] `LLMResponse` enthält: `text`, `model`, `usage` (input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens), `stop_reason`.
- [ ] Logging pro Call (strukturiert): `model`, `tier`, `tokens_in`, `tokens_out`, `cache_read`, `cache_create`, `latency_ms`.
- [ ] API-Key aus `Settings.anthropic_api_key` (env: `ANTHROPIC_API_KEY`).
- [ ] Integration-Test (`pytest`, markiert `@pytest.mark.live`, default skipped):
  - Coaching-System-Prompt (~1500 Tokens) wird zweimal hintereinander mit verschiedenen User-Messages geschickt.
  - Erster Call: `cache_creation_input_tokens > 0`.
  - Zweiter Call: `cache_read_input_tokens > 0` und `> 0.9 * tokens des ersten cache_create`.
- [ ] Unit-Test (default, kein API-Key nötig): Mock des Anthropic-Clients, prüfe dass `tier="cheap"` Haiku-Model-ID an den SDK-Call übergibt und `cache_control` auf System-Block gesetzt ist.

## Datenmodell-Änderungen
Keine (Cost-Tracking-Persistenz erst in späterer Phase).

## API-Änderungen
Keine HTTP-Endpoints in dieser Spec. Der Gateway ist ein internes Service-Objekt.

## UI-Änderungen
Keine.

## LLM-Calls
- **Modell:** Sonnet (default), Haiku (cheap), Opus (hard).
- **Prompt-Caching:** ja, immer auf `system`. Optional auf statischem RAG-Kontext.
- **Erwartete Tokens pro Call (Test-Coaching):**
  - System ~1500 in (gecacht ab 2. Call)
  - User ~50 in
  - Output ~300

## Tests
- Unit (`tests/test_llm_gateway.py`):
  - `test_routing_dispatches_correct_model`: Mock-Client, prüfe Model-ID je Tier.
  - `test_system_prompt_gets_cache_control`: Mock-Client, prüfe Request-Body.
  - `test_response_parses_usage`: Mock-Client gibt Beispiel-Response, `LLMResponse.usage` korrekt extrahiert.
- Live-Integration (`tests/test_llm_gateway_live.py`, `@pytest.mark.live`):
  - `test_caching_works`: zwei Calls, Assertion auf `cache_read_input_tokens` im zweiten.
  - Nur ausgeführt mit `pytest -m live` und gesetztem `ANTHROPIC_API_KEY`.

## Offene Fragen
- Cache-TTL: Anthropic-Default 5 min reicht? Oder 1h-Cache (`cache_control.type = "ephemeral"` mit `ttl: "1h"`) für teurere Calls? — Phase 0: Default 5 min. Falls Coaching-Sessions länger werden, in Phase 2 auf 1h.
- Retry-Logik bei `overloaded_error`? — Ja: 3 Retries mit Exponential-Backoff (2s, 4s, 8s). Per `tenacity` oder eigener Loop.
- Soll `hard`-Tier aktuell wirklich Opus sein, oder bis Phase 3 (Beweise) auf Sonnet bleiben? — Auf Opus mappen, aber im Code dokumentieren, dass `hard` nur für Beweis-Verifikation aufgerufen wird.
