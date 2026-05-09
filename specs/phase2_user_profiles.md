# Spec: User Profile & Preferences

> Status: `implemented`
> Phase: 2
> Verwandte Research: [research/04_system_architecture.md](../research/04_system_architecture.md) · [research/05_ui_ux_design.md](../research/05_ui_ux_design.md)

## Ziel

Der User kann in `/settings` seinen Anzeigenamen und seine wöchentliche Zeitverfügbarkeit pro Tag eintragen; diese Daten persistieren in der DB und werden von der Plan-Engine (Spec 2.6) ausgewertet.

## Nicht-Ziel

- Sessionplan-Generierung oder FSRS-Priorisierung (→ Spec 2.6)
- Multi-User, Auth, Login
- Notifications / Reminder
- Gamification (Streaks, XP)
- Mobile-Layout

## Akzeptanzkriterien

- [ ] `GET /me` gibt `display_name`, `weekly_availability_minutes`, `max_session_minutes` zurück
- [ ] `PATCH /me` persistiert geänderte Felder; nicht gesendete Felder bleiben unverändert
- [ ] Beim ersten `GET /me` (leere DB) wird ein Default-Datensatz automatisch angelegt (kein 404)
- [ ] `/settings` zeigt 7 Tages-Felder (Mo–So, Minuten) + Display-Name + Max-Session-Dauer
- [ ] Änderungen in `/settings` werden nach Speichern sofort im `GET /me`-Response reflektiert
- [ ] `pytest -m "not live"` bleibt grün, `npm test` + `npm run build` bleiben grün

## Datenmodell-Änderungen

Neue Tabelle `user_preferences`. Single-Row-Pattern: immer genau ein Eintrag (id = fester UUID-String `"default"`).

```sql
CREATE TABLE user_preferences (
    id                           TEXT PRIMARY KEY,          -- immer "default"
    display_name                 TEXT,                      -- nullable
    weekly_availability_minutes  TEXT NOT NULL,             -- JSON: {"mon":180,"tue":0,...}
    max_session_minutes          INTEGER NOT NULL DEFAULT 90,
    created_at                   DATETIME NOT NULL,
    updated_at                   DATETIME NOT NULL
);
```

SQLAlchemy-Model (`backend/app/db/models/user_preferences.py`):

```python
class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String(100))
    weekly_availability_minutes: Mapped[dict] = mapped_column(JSON, nullable=False)
    max_session_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
```

Default-Wert für `weekly_availability_minutes`:
```json
{"mon": 120, "tue": 120, "wed": 120, "thu": 120, "fri": 120, "sat": 0, "sun": 0}
```

Alembic-Migration: `<hash>_user_preferences.py` (autogenerate, dann umbenennen).

## API-Änderungen

### `GET /me`

Bestehender Endpoint wird erweitert. Legt Default-Datensatz an, falls keiner existiert.

```
GET /me
Response 200:
{
  "id": "default",
  "display_name": "Dominique" | null,
  "weekly_availability_minutes": {"mon": 120, "tue": 120, "wed": 120, "thu": 120, "fri": 120, "sat": 0, "sun": 0},
  "max_session_minutes": 90
}
```

### `PATCH /me`

Alle Felder optional (Partial Update). Aktualisiert `updated_at`.

```
PATCH /me
Request (alle Felder optional):
{
  "display_name": "Dominique",
  "weekly_availability_minutes": {"mon": 180, "tue": 0, "wed": 180, "thu": 120, "fri": 60, "sat": 0, "sun": 0},
  "max_session_minutes": 90
}
Response 200: (vollständiges Objekt, identisch zu GET /me)
```

Validierung:
- `max_session_minutes`: 15–180 (außerhalb → 422)
- `weekly_availability_minutes`: alle 7 Schlüssel `mon`–`sun` müssen vorhanden sein, Werte 0–480 (außerhalb → 422)

### Pydantic Schemas (`backend/app/api/schemas/me.py`)

```python
class WeeklyAvailability(BaseModel):
    mon: int = Field(ge=0, le=480)
    tue: int = Field(ge=0, le=480)
    wed: int = Field(ge=0, le=480)
    thu: int = Field(ge=0, le=480)
    fri: int = Field(ge=0, le=480)
    sat: int = Field(ge=0, le=480)
    sun: int = Field(ge=0, le=480)

class UserProfileResponse(BaseModel):
    id: str
    display_name: str | None
    weekly_availability_minutes: WeeklyAvailability
    max_session_minutes: int

class UserProfileUpdate(BaseModel):
    display_name: str | None = None
    weekly_availability_minutes: WeeklyAvailability | None = None
    max_session_minutes: int | None = Field(default=None, ge=15, le=180)
```

## UI-Änderungen

Neue Route `/settings` im App Router (`frontend/app/settings/page.tsx`).

```
┌─────────────────────────────────────────────────────────┐
│  Einstellungen                                          │
├─────────────────────────────────────────────────────────┤
│  Name                                                   │
│  ┌─────────────────────────────────────────┐            │
│  │  Dominique                              │            │
│  └─────────────────────────────────────────┘            │
│                                                         │
│  Wöchentliche Verfügbarkeit (Minuten pro Tag)           │
│  Mo  Di  Mi  Do  Fr  Sa  So                             │
│  [180][120][180][120][ 60][  0][  0]                    │
│                                                         │
│  Max. Session-Dauer                                     │
│  [ 90 ] Minuten                                         │
│                                                         │
│                              [ Speichern ]              │
└─────────────────────────────────────────────────────────┘
```

Komponenten:
- `frontend/app/settings/page.tsx` — Settings-Page (Client Component, `"use client"`)
- Formular mit `useState`, `PATCH /me` on Submit
- Keine KaTeX/Mathe nötig
- Navigation: Zahnrad-Icon oder Link in bestehender Nav (falls vorhanden)

## LLM-Calls

Keine — reine CRUD-Operation.

## Tests

**Backend (pytest):**
- `tests/test_me.py` — erweitern:
  - `GET /me` ohne vorherigen Eintrag → 200 + Default-Werte
  - `GET /me` nach Anlegen → korrekte Felder
  - `PATCH /me` mit teilweise gesendeten Feldern → nur geänderte Felder aktualisiert
  - `PATCH /me` mit `max_session_minutes=5` → 422
  - `PATCH /me` mit `weekly_availability_minutes.mon=600` → 422
  - `GET /me` zweimal hintereinander → kein zweiter Default-Eintrag (Single-Row bleibt)

**Frontend (Vitest):**
- `tests/settings.test.tsx`:
  - Settings-Page rendert 7 Tages-Felder
  - Werte aus `GET /me` werden in Felder vorgeladen
  - Submit feuert `PATCH /me` mit korrekten Daten

**Manuell:**
- `/settings` öffnen, Werte ändern, speichern, Seite neu laden → Werte persistiert

## Offene Fragen

- Soll die `/settings`-Route auch in der Hauptnavigation verlinkt sein, oder reicht ein direkter URL-Aufruf für jetzt?
- Braucht `display_name` eine Mindestlänge-Validierung (z. B. min 1 Zeichen wenn gesetzt)?
