'use client'
import { useCallback, useEffect, useRef, useState } from 'react'
import { ChatInput } from './ChatInput'
import { ChatTurn, type Turn } from './ChatTurn'
import { CoachingSummary } from './CoachingSummary'
import { CoachingQuiz, type QuizQuestion } from './CoachingQuiz'

interface Props {
  courseId: string
  conceptId: string
  onEnd?: () => void
}

interface SSEStreamEvent {
  type: 'delta' | 'done' | 'error'
  text?: string
  ready?: boolean
  tokens_in?: number
  tokens_out?: number
  cache_read?: number
  message?: string
}

type Phase =
  | 'creating'
  | 'opening'
  | 'idle'
  | 'streaming'
  | 'concluding'
  | 'summary'
  | 'quiz'
  | 'complete'
  | 'error'

const CHAT_PHASES: Phase[] = ['creating', 'opening', 'idle', 'streaming', 'error']

async function* parseSSE(response: Response): AsyncGenerator<SSEStreamEvent> {
  if (!response.body) throw new Error('No response body')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    // SSE events are separated by blank lines
    const events = buffer.split('\n\n')
    buffer = events.pop() ?? '' // keep last (potentially incomplete) chunk

    for (const ev of events) {
      const dataLine = ev.split('\n').find((l) => l.startsWith('data: '))
      if (!dataLine) continue
      try {
        yield JSON.parse(dataLine.slice(6)) as SSEStreamEvent
      } catch {
        // ignore malformed event line
      }
    }
  }
}

interface ConceptInfo {
  id: string
  name?: string | null
}

interface Conclusion {
  summary: string | null
  quiz: QuizQuestion[]
}

export function CoachingSession({ courseId, conceptId, onEnd }: Props) {
  const [turns, setTurns] = useState<Turn[]>([])
  const [streamingText, setStreamingText] = useState<string>('')
  const [phase, setPhase] = useState<Phase>('creating')
  const [error, setError] = useState<string | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [concept, setConcept] = useState<ConceptInfo>({ id: conceptId })
  const [coachReady, setCoachReady] = useState(false)
  const [conclusion, setConclusion] = useState<Conclusion | null>(null)
  const [endStats, setEndStats] = useState<{ duration_min: number; turn_count: number } | null>(
    null
  )

  const turnsEndRef = useRef<HTMLDivElement>(null)

  // Fetch concept name for the header (best effort)
  useEffect(() => {
    fetch(`/api/courses/${courseId}/concepts`)
      .then((r) => (r.ok ? r.json() : []))
      .then((items: { id: string; name?: string | null }[]) => {
        const c = items.find((x) => x.id === conceptId)
        if (c) setConcept({ id: c.id, name: c.name })
      })
      .catch(() => {})
  }, [courseId, conceptId])

  const streamTurn = useCallback(async (sid: string, userMessage: string) => {
    setPhase('streaming')
    setStreamingText('')
    setCoachReady(false)
    try {
      const response = await fetch(`/api/coaching/sessions/${sid}/turn`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_message: userMessage }),
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      let assistantText = ''
      for await (const event of parseSSE(response)) {
        if (event.type === 'delta' && event.text) {
          assistantText += event.text
          setStreamingText(assistantText)
        } else if (event.type === 'done') {
          // Finalize the assistant turn (triggers Markdown/KaTeX rerender)
          setTurns((prev) => [...prev, { role: 'assistant', content: assistantText }])
          setStreamingText('')
          setCoachReady(event.ready === true)
          setPhase('idle')
        } else if (event.type === 'error') {
          throw new Error(event.message ?? 'Stream error')
        }
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Unknown error'
      setError(msg)
      setStreamingText('')
      setPhase('error')
    }
  }, [])

  // Create session on mount, then trigger opening turn
  useEffect(() => {
    let cancelled = false
    async function start() {
      try {
        const r = await fetch('/api/coaching/sessions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ course_id: courseId, concept_id: conceptId }),
        })
        if (!r.ok) throw new Error(`Create session failed: HTTP ${r.status}`)
        const data: { session_id: string } = await r.json()
        if (cancelled) return
        setSessionId(data.session_id)
        setPhase('opening')
        await streamTurn(data.session_id, '')
      } catch (e) {
        const msg = e instanceof Error ? e.message : 'Unknown error'
        if (!cancelled) {
          setError(msg)
          setPhase('error')
        }
      }
    }
    start()
    return () => {
      cancelled = true
    }
  }, [courseId, conceptId, streamTurn])

  // Auto-scroll to bottom on new content (jsdom in tests doesn't implement scrollIntoView)
  useEffect(() => {
    turnsEndRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'end' })
  }, [turns, streamingText])

  const handleSend = useCallback(
    (message: string) => {
      if (!sessionId || phase !== 'idle') return
      setTurns((prev) => [...prev, { role: 'user', content: message }])
      streamTurn(sessionId, message)
    },
    [sessionId, phase, streamTurn]
  )

  const finish = useCallback(() => {
    setPhase('complete')
    onEnd?.()
  }, [onEnd])

  const handleEnd = useCallback(async () => {
    if (!sessionId) return
    setPhase('concluding')
    let summary: string | null = null
    let quiz: QuizQuestion[] = []
    let stats: { duration_min: number; turn_count: number } | null = null
    try {
      const r = await fetch(`/api/coaching/sessions/${sessionId}/end`, { method: 'POST' })
      if (r.ok) {
        const data = await r.json()
        stats = { duration_min: data.duration_min, turn_count: data.turn_count }
        summary = data.summary ?? null
        quiz = Array.isArray(data.quiz) ? data.quiz : []
      }
    } catch {
      // best effort — fall through to the conclusion screen with empty data
    }
    setEndStats(stats)
    setConclusion({ summary, quiz })
    setPhase('summary')
  }, [sessionId])

  const turnCount = turns.filter((t) => t.role === 'assistant').length + (streamingText ? 1 : 0)
  const conceptLabel = concept.name ?? concept.id
  const isStreaming = phase === 'streaming' || phase === 'opening'
  const isChatPhase = CHAT_PHASES.includes(phase)
  const quiz = conclusion?.quiz ?? []

  return (
    <div className="min-h-[calc(100vh-3.5rem)] flex flex-col">
      {/* Header */}
      <header
        className="flex items-center justify-between px-6 py-4 border-b"
        style={{ borderColor: 'var(--border)' }}
      >
        <div className="flex items-baseline gap-3">
          <span className="font-semibold tracking-tight" style={{ color: 'var(--text)' }}>
            Coaching · {conceptLabel}
          </span>
          <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
            {turnCount} Turns
          </span>
        </div>
        {isChatPhase && (
          <button
            onClick={handleEnd}
            className="px-3 py-1.5 text-sm rounded-lg font-medium transition-colors"
            style={
              coachReady
                ? { backgroundColor: 'var(--accent)', color: 'var(--bg)' }
                : { border: '1px solid var(--border)', color: 'var(--text-muted)' }
            }
          >
            {coachReady ? 'Konzept verstanden — beenden' : 'Ende'}
          </button>
        )}
      </header>

      {/* Conclusion flow */}
      {phase === 'concluding' && (
        <main className="flex-1 flex items-center justify-center px-6">
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            Zusammenfassung wird erstellt …
          </p>
        </main>
      )}

      {phase === 'summary' && conclusion && (
        <main className="flex-1 px-6 py-8">
          <div className="max-w-2xl mx-auto">
            <CoachingSummary
              summary={conclusion.summary}
              primary={
                quiz.length > 0
                  ? { label: 'Zum Quiz →', onClick: () => setPhase('quiz') }
                  : { label: 'Abschließen', onClick: finish }
              }
              secondary={quiz.length > 0 ? { label: 'Überspringen', onClick: finish } : undefined}
            />
          </div>
        </main>
      )}

      {phase === 'quiz' && (
        <main className="flex-1 px-6 py-8">
          <div className="max-w-2xl mx-auto">
            <CoachingQuiz quiz={quiz} onComplete={finish} onSkip={finish} />
          </div>
        </main>
      )}

      {phase === 'complete' && (
        <main className="flex-1 flex items-center justify-center px-6">
          <div
            className="text-center py-6 px-10 rounded-2xl"
            style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)' }}
          >
            <p className="font-medium" style={{ color: 'var(--text)' }}>
              Session abgeschlossen
            </p>
            {endStats && (
              <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
                {endStats.turn_count} Turns · {endStats.duration_min.toFixed(1)} min
              </p>
            )}
          </div>
        </main>
      )}

      {/* Chat area */}
      {isChatPhase && (
        <main className="flex-1 overflow-y-auto px-6 pt-8 pb-4">
          <div className="max-w-3xl mx-auto flex flex-col gap-7">
            {turns.map((t, i) => (
              <ChatTurn key={i} turn={t} />
            ))}

            {streamingText && (
              <ChatTurn turn={{ role: 'assistant', content: streamingText }} streaming />
            )}

            {(phase === 'creating' || phase === 'opening') && !streamingText && (
              <p className="text-center text-sm" style={{ color: 'var(--text-muted)' }}>
                Session wird gestartet …
              </p>
            )}

            {error && (
              <div
                role="alert"
                className="px-4 py-3 rounded-lg text-sm"
                style={{
                  backgroundColor: 'rgba(239,68,68,0.1)',
                  border: '1px solid rgba(239,68,68,0.3)',
                  color: '#fca5a5',
                }}
              >
                {error}
              </div>
            )}

            <div ref={turnsEndRef} />
          </div>
        </main>
      )}

      {/* Input — lifted off the bottom edge with a fade behind it */}
      {isChatPhase && (
        <div
          className="sticky bottom-0 px-6 pt-3 pb-7"
          style={{
            background:
              'linear-gradient(to top, var(--bg) 55%, color-mix(in srgb, var(--bg) 70%, transparent) 80%, transparent)',
          }}
        >
          <div className="max-w-3xl mx-auto">
            <ChatInput
              onSend={handleSend}
              disabled={isStreaming || phase === 'creating' || phase === 'error'}
            />
          </div>
        </div>
      )}
    </div>
  )
}
