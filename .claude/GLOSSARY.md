# Ubiquitous Language — StudyAssistant

> Dieses Glossar ist die kanonische Domänen-Sprache für Claude und den Entwickler.
> Claude Code spricht in diesen Begriffen. Code-Identifier folgen diesen Konzepten.

---

## Kerndomäne: Lernen & Kognition

| Begriff | Kürzel | Definition | Code-Entsprechung |
|---|---|---|---|
| **Course** | — | Lehrveranstaltung (z.B. „Deep Learning", „Statistik II"). Oberste Aggregationseinheit. | `models/courses.py` · `Course` |
| **Material** | — | Hochgeladenes Dokument (PDF, Video, Text) das zu einem Course gehört. Rohquelle für Concept-Extraktion. | `models/materials.py` · `Material` |
| **Concept** | — | Atomares Lernziel, extrahiert aus einem Material. Hat eine Schwierigkeit und optional einen Eltern-Concept (Hierarchie). | `models/concepts.py` · `Concept` |
| **Card** | — | Frage-Antwort-Paar zu einem Concept. Grundeinheit des Active Recall. Enthält FSRS-State. | `models/cards.py` · `Card` |
| **Review** | — | Eine einzelne Beurteilungs-Session einer Card (Rating 1–4, Zeitstempel, nächstes Fälligkeitsdatum). | `models/reviews.py` · `Review` |
| **WorkedExample** | — | Durchgerechnetes Beispiel zu einem Concept (mit optionalem Code-Block). Zeigt Anwendung, nicht Theorie. | `models/worked_examples.py` · `WorkedExample` |
| **Quiz** | — | Zeitgebundene Aufgabensammlung zu einem Course. Mehrere Fragen, Bestehschwelle. | `models/quiz.py` · `Quiz` |
| **MockExam** | — | Simulierte Prüfung mit Zeitlimit und Fragensatz. Höhere Kognitionsstufe als Quiz. | `models/mock_exams.py` · `MockExam` |
| **Plan** | — | Strukturierter Lernplan (JSON: Roadmap + Meilensteine) für einen Course. Enthält Status. | `models/plans.py` · `Plan` |
| **Coaching** | — | Eine Frage-Antwort-Runde im Sokratischen Dialog. Enthält Student-Message, Tutor-Response, Qualitäts-Feedback. | `models/coaching.py` · `Coaching` |

---

## Lernwissenschaft

| Begriff | Definition | Implementierung |
|---|---|---|
| **Active Recall** | Wissen aktiv abrufen (nicht passiv lesen). Basis für Card-Reviews. | Card → Review-Cycle |
| **Spaced Repetition** | Wiederholung zum optimalen Zeitpunkt kurz vor dem Vergessen. | `py-fsrs` direkt |
| **FSRS** | Free Spaced Repetition Scheduler — State-of-the-Art Algorithmus für Intervall-Berechnung. Kein eigener Heuristik-Code. | `Card.fsrs_state` (JSON) |
| **FSRS-State** | JSON-Blob mit FSRS-internem Gedächtniszustand (stability, difficulty, retrievability). Wird nach jedem Review durch py-fsrs aktualisiert. | `Card.fsrs_state` |
| **Rating** | Selbstbeurteilung nach einem Review: 1=Again, 2=Hard, 3=Good, 4=Easy. | `Review.rating` |
| **Interval** | Tage bis zum nächsten Review. Vom FSRS-Algorithmus berechnet. | `Review.interval` |
| **Ease Factor** | Schwierigkeitsmultiplikator im FSRS-Modell. Beeinflusst Intervall-Wachstum. | `Review.ease_factor` |
| **Sokratisches Coaching** | Dialog-basierte Lernmethode: Tutor stellt Fragen statt Antworten zu geben. System verwendet Sonnet (default-tier). | `Coaching` + LLMGateway |
| **Review-Queue** | Liste der heute fälligen Cards (nach FSRS-Fälligkeitsdatum sortiert). Herzstück der Daily-Review-UI. | Phase 1.4 |

---

## Ingest & RAG

| Begriff | Definition | Implementierung |
|---|---|---|
| **Ingest-Pipeline** | Verarbeitungskette: PDF → Text → Chunks → Embeddings → Chroma. Läuft nach Material-Upload. | Phase 1.2 |
| **Chunk** | Textsegment ~500 Tokens aus einem Material. Einheit für Embedding und Retrieval. | Tiktoken-basiert |
| **Embedding** | Vektorrepräsentation eines Chunks. Ermöglicht semantische Suche. | OpenAI text-embedding-3-small |
| **Chroma** | Lokale Vektor-Datenbank (file-based). Speichert Embeddings + Metadata für RAG-Queries. | `data/chroma/` |
| **RAG-Kontext** | Retrieval-Augmented Generation: relevante Chunks werden als Kontext in den LLM-Prompt geladen. Cache-Breakpoint-tauglich. | `LLMGateway.complete(cache_breakpoints=...)` |
| **Concept-Extraktion** | LLM-gestütztes Identifizieren von Concepts aus einem Material-Text. Resultat landet in Review-Queue. | Phase 1.2 · cheap-tier |
| **marker-pdf** | Math-aware PDF → Markdown Konverter. Erste Wahl für PDFs. Fallback: pymupdf. | `backend/app/services/pdf_parser.py` (Phase 1.1) |

---

## LLM & Gateway

| Begriff | Definition | Implementierung |
|---|---|---|
| **LLM Gateway** | Zentraler Einstiegspunkt für alle Anthropic-API-Calls. Kapselt Retry, Caching, Logging. | `services/llm_gateway.py` |
| **Tier** | Qualitäts-/Kosten-Level für LLM-Calls: `default` (Sonnet), `cheap` (Haiku), `hard` (Opus). | `services/llm_models.py` · `Tier` |
| **Prompt Caching** | Anthropic-Feature: wiederholte System-Prompts werden gecacht (TTL 5 min). System-Block bekommt `cache_control`. | `LLMGateway._call()` |
| **Cache Breakpoint** | Markierung in der Message-Liste, ab der Anthropic den Kontext cached. Für statischen RAG-Kontext. | `LLMGateway.complete(cache_breakpoints=...)` |
| **Retry-Logik** | 3 Versuche bei HTTP 529 (Overloaded) mit exponentiellem Backoff (2s→4s→8s). Via Tenacity. | `@retry` in `LLMGateway._call()` |
| **Streaming** | SSE (Server-Sent Events) für Echtzeit-Ausgabe des Tutors im Coaching-Dialog. | Phase 1.5 |
| **default-tier** | `claude-sonnet-4-6` — Standard für Coaching, Konzept-Extraktion. | `TIER_MODEL_MAP["default"]` |
| **cheap-tier** | `claude-haiku-4-5-20251001` — Für Bulk-Tasks (Karten-Generierung, Klassifikation). | `TIER_MODEL_MAP["cheap"]` |
| **hard-tier** | `claude-opus-4-7` — Für mathematische Beweise, komplexe Sachverhalte. | `TIER_MODEL_MAP["hard"]` |

---

## Architektur & Infrastruktur

| Begriff | Definition | Implementierung |
|---|---|---|
| **DeclarativeBase** | SQLAlchemy 2.x Basisklasse. Alle Models erben davon. Kein `Column()` — nur `Mapped[]`. | `db/base.py` |
| **Alembic Migration** | Versionierter Schema-Change. `render_as_batch=True` für SQLite-Kompatibilität. | `alembic/versions/` |
| **Settings** | Pydantic V2 BaseSettings. Liest `.env`. `SettingsConfigDict`, nicht `class Config`. | `core/config.py` |
| **JSON-Logger** | Strukturiertes Logging mit Extra-Feldern (model, tier, tokens, latency). | `core/logging.py` |
| **Health-Endpoint** | `GET /health` — gibt Status + DB-Check zurück. Monitoring-Einstiegspunkt. | `api/health.py` |
| **`uv`** | Python Package Manager (schneller als pip/poetry). Alle Backend-Deps via `uv sync`. | `uv.lock` |
| **`py-fsrs`** | Offizielle Python-Implementierung des FSRS-Algorithmus. Keine eigenen Heuristiken. | Phase 1.3 |

---

## Was wir NICHT sagen / tun

| Vermeiden | Stattdessen |
|---|---|
| „Gamification", „XP", „Streaks" | — (nicht im Scope, nie einbauen) |
| „Auto-generierte Karten direkt speichern" | „Review-Queue — User muss bestätigen" |
| „Mobile-First" | „Desktop-first, responsive sekundär" |
| `Column(...)` (SQLAlchemy 1.x) | `Mapped[...] = mapped_column(...)` |
| `class Config:` (Pydantic V1) | `model_config = SettingsConfigDict(...)` |
| Eigene Spaced-Repetition-Logik | `py-fsrs` direkt |
| Direkter `anthropic.Anthropic()`-Call | `LLMGateway.complete()` |

---

*Letzte Aktualisierung: Phase 0 abgeschlossen, Phase 1 geplant (2026-05-08)*
