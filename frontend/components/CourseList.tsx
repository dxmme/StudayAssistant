'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'

interface Course {
  id: string
  name: string
  exam_date: string
  semester?: string | null
  professor?: string | null
}

interface CourseListProps {
  onDeleted?: () => void
}

export function CourseList({ onDeleted }: CourseListProps) {
  const [courses, setCourses] = useState<Course[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [confirmId, setConfirmId] = useState<string | null>(null)

  useEffect(() => {
    fetch('http://localhost:8000/api/courses')
      .then(r => r.json())
      .then(setCourses)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  function requestDelete(e: React.MouseEvent, courseId: string) {
    e.preventDefault()
    e.stopPropagation()
    setConfirmId(courseId)
  }

  async function confirmDelete(courseId: string) {
    setConfirmId(null)
    setDeletingId(courseId)
    try {
      const res = await fetch(`http://localhost:8000/api/courses/${courseId}`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Löschen fehlgeschlagen')
      setCourses(prev => prev.filter(c => c.id !== courseId))
      onDeleted?.()
    } catch {
      alert('Kurs konnte nicht gelöscht werden.')
    } finally {
      setDeletingId(null)
    }
  }

  if (loading) return <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Lädt…</p>
  if (error) return <p className="text-sm text-red-500">Fehler: {error}</p>
  if (courses.length === 0) return (
    <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
      Noch keine Kurse. Erstelle deinen ersten Kurs.
    </p>
  )

  return (
    <div className="space-y-2">
      {courses.map(course => (
        <div
          key={course.id}
          className="group flex items-center gap-3 rounded-xl transition-all"
          style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)' }}
        >
          <Link
            href={`/courses/${course.id}`}
            className="flex-1 p-4 min-w-0"
          >
            <h3 className="font-medium text-sm truncate" style={{ color: 'var(--text)' }}>
              {course.name}
            </h3>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
              Klausur: {new Date(course.exam_date).toLocaleDateString('de-DE')}
              {course.professor && ` · ${course.professor}`}
            </p>
          </Link>

          {confirmId === course.id ? (
            <div className="flex items-center gap-2 mr-3 shrink-0" onClick={e => e.preventDefault()}>
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Löschen?</span>
              <button
                onClick={() => confirmDelete(course.id)}
                className="text-xs px-2 py-1 rounded-md font-medium"
                style={{ backgroundColor: '#ef4444', color: '#fff' }}
              >
                Ja
              </button>
              <button
                onClick={e => { e.preventDefault(); setConfirmId(null) }}
                className="text-xs px-2 py-1 rounded-md font-medium"
                style={{ backgroundColor: 'var(--surface-raised)', color: 'var(--text)' }}
              >
                Nein
              </button>
            </div>
          ) : (
            <button
              onClick={e => requestDelete(e, course.id)}
              disabled={deletingId === course.id}
              className="mr-3 p-1.5 rounded-md transition-all"
              style={{ color: 'var(--text-dim)' }}
              title="Kurs löschen"
              aria-label="Kurs löschen"
            >
              {deletingId === course.id ? (
                <svg className="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                </svg>
              ) : (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="3 6 5 6 21 6" />
                  <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                  <path d="M10 11v6M14 11v6" />
                  <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
                </svg>
              )}
            </button>
          )}
        </div>
      ))}
    </div>
  )
}
