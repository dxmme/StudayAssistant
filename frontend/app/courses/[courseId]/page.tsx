'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import React, { useEffect, useState } from 'react'

interface Course {
  id: string
  name: string
  exam_date: string
  semester?: string | null
  professor?: string | null
}

interface CourseDetailPageProps {
  params: Promise<{ courseId: string }>
}

function IconUpload() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  )
}

function IconLayers() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 2 7 12 12 22 7 12 2" />
      <polyline points="2 17 12 22 22 17" />
      <polyline points="2 12 12 17 22 12" />
    </svg>
  )
}

function IconCards() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="4" width="20" height="16" rx="2" />
      <path d="M7 15h0M12 15h0M17 15h0" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M7 10h10" />
    </svg>
  )
}

function IconGraph() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="5" cy="12" r="2" />
      <circle cx="19" cy="5" r="2" />
      <circle cx="19" cy="19" r="2" />
      <line x1="7" y1="11.5" x2="17" y2="6.5" />
      <line x1="7" y1="12.5" x2="17" y2="17.5" />
    </svg>
  )
}

function IconCalendar() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  )
}

export default function CourseDetailPage({ params }: CourseDetailPageProps) {
  const { courseId } = React.use(params)
  const router = useRouter()
  const [course, setCourse] = useState<Course | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`http://localhost:8000/api/courses/${courseId}`)
      .then(r => r.json())
      .then(setCourse)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [courseId])

  if (loading) return (
    <div className="min-h-[calc(100vh-3.5rem)] flex items-center justify-center">
      <p style={{ color: 'var(--text-muted)' }} className="text-sm">Lädt…</p>
    </div>
  )
  if (error) return (
    <div className="min-h-[calc(100vh-3.5rem)] flex items-center justify-center">
      <p className="text-sm text-red-500">Fehler: {error}</p>
    </div>
  )
  if (!course) return (
    <div className="min-h-[calc(100vh-3.5rem)] flex items-center justify-center">
      <p style={{ color: 'var(--text-muted)' }} className="text-sm">Kurs nicht gefunden</p>
    </div>
  )

  const sections = [
    { title: 'Materialien', href: `/courses/${courseId}/materials`, desc: 'PDFs hochladen & ingesten', Icon: IconUpload },
    { title: 'Konzepte', href: `/courses/${courseId}/concepts`, desc: 'Extrahierte Konzepte', Icon: IconLayers },
    { title: 'Lernkarten', href: `/review/${courseId}`, desc: 'Review-Session (FSRS)', Icon: IconCards },
    { title: 'Tagesplan', href: '/plan', desc: 'Heutige Lerneinheit', Icon: IconCalendar },
    { title: 'Concept Graph', href: `/courses/${courseId}/graph`, desc: 'Abhängigkeiten visualisieren', Icon: IconGraph },
  ]

  return (
    <div className="min-h-[calc(100vh-3.5rem)] py-12">
      <div className="max-w-3xl mx-auto px-6">
        <Link
          href="/courses"
          className="inline-flex items-center gap-1.5 text-sm mb-8 transition-colors"
          style={{ color: 'var(--text-muted)' }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 12H5M12 5l-7 7 7 7" />
          </svg>
          Alle Kurse
        </Link>

        <div className="mb-10">
          <h1 className="text-2xl font-semibold mb-1 tracking-tight" style={{ color: 'var(--text)' }}>
            {course.name}
          </h1>
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            Klausur: {new Date(course.exam_date).toLocaleDateString('de-DE')}
            {course.professor && ` · ${course.professor}`}
          </p>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          {sections.map((section) => (
            <Link
              key={section.href}
              href={section.href}
              className="flex items-start gap-4 p-5 rounded-xl transition-all group"
              style={{
                backgroundColor: 'var(--surface)',
                border: '1px solid var(--border)',
              }}
            >
              <div
                className="mt-0.5 p-2 rounded-lg"
                style={{ backgroundColor: 'var(--surface-2)', color: 'var(--text-muted)' }}
              >
                <section.Icon />
              </div>
              <div>
                <h3 className="font-medium text-sm mb-0.5" style={{ color: 'var(--text)' }}>
                  {section.title}
                </h3>
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  {section.desc}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
