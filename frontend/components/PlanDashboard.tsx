'use client'

import { useEffect, useState } from 'react'

interface Course {
  id: string
  name: string
  exam_date: string | null
}

interface PlanItem {
  type: 'card_review' | 'new_concept' | 'coaching'
  title: string
  estimated_min: number
  done: boolean
  concept_id: string | null
  card_count: number | null
}

interface PlanSession {
  id: string
  course_id: string | null
  scheduled_date: string | null
  duration_min: number | null
  items: PlanItem[]
  status: string
  completed_at: string | null
}

interface CourseWithPlan {
  course: Course
  plan: PlanSession
}

type Phase = 'loading' | 'ready' | 'empty' | 'error'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000'

function daysUntilExam(examDate: string | null): number | null {
  if (!examDate) return null
  const diff = new Date(examDate).getTime() - Date.now()
  return Math.ceil(diff / (1000 * 60 * 60 * 24))
}

function planPhaseLabel(examDate: string | null): string {
  const days = daysUntilExam(examDate)
  if (days === null) return 'Semester Companion'
  if (days > 42) return 'Semester Companion'
  if (days > 14) return 'Active Preparation'
  if (days > 3) return 'Consolidation'
  return 'Final Review'
}

function itemTypeLabel(type: PlanItem['type']): string {
  if (type === 'card_review') return 'Karteikarten-Review'
  if (type === 'new_concept') return 'Neues Konzept'
  return 'Coaching'
}

async function fetchPlan(courseId: string): Promise<PlanSession> {
  const r = await fetch(`${BACKEND}/api/courses/${courseId}/plan/today`, {
    method: 'POST',
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json() as Promise<PlanSession>
}

async function markItemDone(planId: string, index: number): Promise<PlanSession> {
  const r = await fetch(`${BACKEND}/api/plans/${planId}/items/${index}/complete`, {
    method: 'PATCH',
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json() as Promise<PlanSession>
}

async function completeSession(planId: string): Promise<PlanSession> {
  const r = await fetch(`${BACKEND}/api/plans/${planId}/complete`, {
    method: 'POST',
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json() as Promise<PlanSession>
}

function PlanSessionCard({
  entry,
  onItemDone,
  onComplete,
}: {
  entry: CourseWithPlan
  onItemDone: (planId: string, index: number) => void
  onComplete: (planId: string) => void
}) {
  const { course, plan } = entry
  const days = daysUntilExam(course.exam_date)
  const completed = plan.status === 'completed'

  return (
    <div
      className="rounded-xl p-5"
      style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)' }}
    >
      <div className="flex justify-between items-start mb-1">
        <h2 className="font-semibold text-sm" style={{ color: 'var(--text)' }}>{course.name}</h2>
        <span className="text-xs ml-2" style={{ color: 'var(--text-muted)' }}>
          {days !== null ? `Klausur in ${days} Tagen` : 'Kein Klausurdatum'}
        </span>
      </div>
      <div className="text-xs mb-4" style={{ color: 'var(--text-muted)' }}>
        {planPhaseLabel(course.exam_date)} &mdash; {plan.duration_min ?? 0} min geplant
      </div>

      {plan.items.length === 0 ? (
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Heute nichts fällig.</p>
      ) : (
        <ul className="space-y-2 mb-4">
          {plan.items.map((item, idx) => (
            <li key={idx} className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={item.done}
                disabled={completed || item.done}
                onChange={() => onItemDone(plan.id, idx)}
                className="h-4 w-4"
                style={{ accentColor: 'var(--accent)' }}
                data-testid={`item-checkbox-${idx}`}
              />
              <span
                className="text-sm flex-1"
                style={{ color: item.done ? 'var(--text-muted)' : 'var(--text)', textDecoration: item.done ? 'line-through' : 'none' }}
              >
                {itemTypeLabel(item.type)} &mdash; {item.title}
              </span>
              <span className="text-xs shrink-0" style={{ color: 'var(--text-muted)' }}>~{item.estimated_min} min</span>
            </li>
          ))}
        </ul>
      )}

      {!completed ? (
        <button
          onClick={() => onComplete(plan.id)}
          className="text-sm font-medium transition-colors"
          style={{ color: 'var(--accent)' }}
          data-testid="complete-button"
        >
          Session abschließen
        </button>
      ) : (
        <span className="text-sm" style={{ color: '#4ade80' }}>Abgeschlossen</span>
      )}
    </div>
  )
}

export function PlanDashboard() {
  const [phase, setPhase] = useState<Phase>('loading')
  const [entries, setEntries] = useState<CourseWithPlan[]>([])

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const r = await fetch(`${BACKEND}/api/courses`)
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        const courses: Course[] = await r.json()

        if (courses.length === 0) {
          if (!cancelled) setPhase('empty')
          return
        }

        const results = await Promise.all(
          courses.map(async (course) => {
            const plan = await fetchPlan(course.id)
            return { course, plan }
          })
        )

        if (!cancelled) {
          setEntries(results)
          setPhase('ready')
        }
      } catch {
        if (!cancelled) setPhase('error')
      }
    }

    load()
    return () => { cancelled = true }
  }, [])

  function handleItemDone(planId: string, index: number) {
    markItemDone(planId, index).then((updated) => {
      setEntries((prev) =>
        prev.map((e) => (e.plan.id === planId ? { ...e, plan: updated } : e))
      )
    })
  }

  function handleComplete(planId: string) {
    completeSession(planId).then((updated) => {
      setEntries((prev) =>
        prev.map((e) => (e.plan.id === planId ? { ...e, plan: updated } : e))
      )
    })
  }

  if (phase === 'loading') {
    return (
      <div className="min-h-[calc(100vh-3.5rem)] py-12">
        <div className="max-w-2xl mx-auto px-6">
          <h1 className="text-2xl font-semibold mb-10 tracking-tight" style={{ color: 'var(--text)' }}>Tagesplan</h1>
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Lade Pläne…</p>
        </div>
      </div>
    )
  }

  if (phase === 'error') {
    return (
      <div className="min-h-[calc(100vh-3.5rem)] py-12">
        <div className="max-w-2xl mx-auto px-6">
          <h1 className="text-2xl font-semibold mb-10 tracking-tight" style={{ color: 'var(--text)' }}>Tagesplan</h1>
          <p className="text-sm text-red-400">Pläne konnten nicht geladen werden.</p>
        </div>
      </div>
    )
  }

  if (phase === 'empty') {
    return (
      <div className="min-h-[calc(100vh-3.5rem)] py-12">
        <div className="max-w-2xl mx-auto px-6">
          <h1 className="text-2xl font-semibold mb-10 tracking-tight" style={{ color: 'var(--text)' }}>Tagesplan</h1>
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Keine Kurse vorhanden.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-[calc(100vh-3.5rem)] py-12">
      <div className="max-w-2xl mx-auto px-6">
      <h1 className="text-2xl font-semibold mb-10 tracking-tight" style={{ color: 'var(--text)' }}>Tagesplan</h1>
      <div className="space-y-4">
        {entries.map((entry) => (
          <PlanSessionCard
            key={entry.plan.id}
            entry={entry}
            onItemDone={handleItemDone}
            onComplete={handleComplete}
          />
        ))}
      </div>
      </div>
    </div>
  )
}
