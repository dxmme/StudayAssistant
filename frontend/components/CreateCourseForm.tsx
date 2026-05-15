'use client'

import { useState } from 'react'

interface CreateCourseFormProps {
  onSuccess?: () => void
}

export function CreateCourseForm({ onSuccess }: CreateCourseFormProps) {
  const [name, setName] = useState('')
  const [semester, setSemester] = useState('')
  const [exam_date, setExamDate] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const res = await fetch('http://localhost:8000/api/courses', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, semester: semester || null, exam_date }),
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Fehler beim Erstellen des Kurses')
      }

      setName('')
      setSemester('')
      setExamDate('')
      onSuccess?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler')
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = {
    backgroundColor: 'var(--surface-2)',
    border: '1px solid var(--border)',
    color: 'var(--text)',
    borderRadius: '8px',
    padding: '8px 12px',
    width: '100%',
    fontSize: '14px',
    outline: 'none',
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4 p-5 rounded-xl"
      style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)' }}
    >
      <h2 className="text-sm font-semibold" style={{ color: 'var(--text)' }}>Neuer Kurs</h2>

      <div>
        <label className="block text-xs mb-1.5" style={{ color: 'var(--text-muted)' }}>
          Kurs Name *
        </label>
        <input
          type="text"
          value={name}
          onChange={e => setName(e.target.value)}
          required
          placeholder="Machine Learning"
          style={inputStyle}
        />
      </div>

      <div>
        <label className="block text-xs mb-1.5" style={{ color: 'var(--text-muted)' }}>
          Semester
        </label>
        <input
          type="text"
          value={semester}
          onChange={e => setSemester(e.target.value)}
          placeholder="SS2026"
          style={inputStyle}
        />
      </div>

      <div>
        <label className="block text-xs mb-1.5" style={{ color: 'var(--text-muted)' }}>
          Klausurdatum *
        </label>
        <input
          type="date"
          value={exam_date}
          onChange={e => setExamDate(e.target.value)}
          required
          style={inputStyle}
        />
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      <button
        type="submit"
        disabled={loading}
        className="w-full py-2 rounded-lg text-sm font-medium transition-all disabled:opacity-40"
        style={{ backgroundColor: 'var(--accent)', color: '#000' }}
      >
        {loading ? 'Wird erstellt…' : 'Kurs erstellen'}
      </button>
    </form>
  )
}
