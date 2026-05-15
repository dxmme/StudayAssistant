'use client'

import { useEffect, useState } from 'react'

type WeeklyAvailability = {
  mon: number
  tue: number
  wed: number
  thu: number
  fri: number
  sat: number
  sun: number
}

type UserProfile = {
  id: string
  display_name: string | null
  weekly_availability_minutes: WeeklyAvailability
  max_session_minutes: number
}

const DAY_LABELS: { key: keyof WeeklyAvailability; label: string }[] = [
  { key: 'mon', label: 'Mo' },
  { key: 'tue', label: 'Di' },
  { key: 'wed', label: 'Mi' },
  { key: 'thu', label: 'Do' },
  { key: 'fri', label: 'Fr' },
  { key: 'sat', label: 'Sa' },
  { key: 'sun', label: 'So' },
]

const DEFAULT_AVAILABILITY: WeeklyAvailability = {
  mon: 120, tue: 120, wed: 120, thu: 120, fri: 120, sat: 0, sun: 0,
}

const inputStyle = {
  backgroundColor: 'var(--surface-2)',
  border: '1px solid var(--border)',
  color: 'var(--text)',
  borderRadius: '8px',
  padding: '8px 12px',
  fontSize: '14px',
  outline: 'none',
  width: '100%',
}

export function SettingsForm() {
  const [displayName, setDisplayName] = useState('')
  const [availability, setAvailability] = useState<WeeklyAvailability>(DEFAULT_AVAILABILITY)
  const [maxSession, setMaxSession] = useState(90)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    fetch('/me')
      .then((r) => r.json())
      .then((data: UserProfile) => {
        setDisplayName(data.display_name ?? '')
        setAvailability(data.weekly_availability_minutes)
        setMaxSession(data.max_session_minutes)
        setLoading(false)
      })
      .catch(() => {
        setError('Einstellungen konnten nicht geladen werden.')
        setLoading(false)
      })
  }, [])

  function handleDayChange(day: keyof WeeklyAvailability, raw: string) {
    const value = Math.max(0, Math.min(480, parseInt(raw, 10) || 0))
    setAvailability((prev) => ({ ...prev, [day]: value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setSaved(false)
    try {
      const r = await fetch('/me', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          display_name: displayName || null,
          weekly_availability_minutes: availability,
          max_session_minutes: maxSession,
        }),
      })
      if (!r.ok) {
        setError('Speichern fehlgeschlagen.')
      } else {
        setSaved(true)
      }
    } catch {
      setError('Netzwerkfehler.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Lade Einstellungen…</p>
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      <div
        className="p-5 rounded-xl space-y-5"
        style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)' }}
      >
        <div>
          <label
            className="block text-xs mb-1.5"
            style={{ color: 'var(--text-muted)' }}
            htmlFor="display-name"
          >
            Name
          </label>
          <input
            id="display-name"
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Dein Name"
            style={inputStyle}
          />
        </div>

        <div>
          <p className="text-xs mb-3" style={{ color: 'var(--text-muted)' }}>
            Wöchentliche Verfügbarkeit (Minuten pro Tag)
          </p>
          <div className="flex gap-2">
            {DAY_LABELS.map(({ key, label }) => (
              <div key={key} className="flex flex-col items-center gap-1 flex-1">
                <label
                  className="text-xs"
                  style={{ color: 'var(--text-muted)' }}
                  htmlFor={`day-${key}`}
                >
                  {label}
                </label>
                <input
                  id={`day-${key}`}
                  type="number"
                  min={0}
                  max={480}
                  value={availability[key]}
                  onChange={(e) => handleDayChange(key, e.target.value)}
                  className="text-center"
                  style={{
                    ...inputStyle,
                    padding: '6px 4px',
                    fontSize: '12px',
                  }}
                  aria-label={`Verfügbarkeit ${label}`}
                />
              </div>
            ))}
          </div>
        </div>

        <div>
          <label
            className="block text-xs mb-1.5"
            style={{ color: 'var(--text-muted)' }}
            htmlFor="max-session"
          >
            Max. Session-Dauer (Minuten)
          </label>
          <input
            id="max-session"
            type="number"
            min={15}
            max={180}
            value={maxSession}
            onChange={(e) => setMaxSession(Math.max(15, Math.min(180, parseInt(e.target.value, 10) || 90)))}
            style={{ ...inputStyle, width: '96px' }}
            aria-label="Maximale Session-Dauer"
          />
        </div>
      </div>

      {error && (
        <p className="text-sm text-red-400" role="alert">{error}</p>
      )}
      {saved && (
        <p className="text-sm" style={{ color: '#4ade80' }} role="status">Gespeichert.</p>
      )}

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={saving}
          className="px-5 py-2 rounded-lg text-sm font-medium transition-all disabled:opacity-40"
          style={{ backgroundColor: 'var(--accent)', color: '#000' }}
        >
          {saving ? 'Speichern…' : 'Speichern'}
        </button>
      </div>
    </form>
  )
}
