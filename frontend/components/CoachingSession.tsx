'use client'
import { useCallback, useEffect, useRef, useState } from 'react'
import { ChatInput } from './ChatInput'
import { ChatTurn, type Turn } from './ChatTurn'

interface Props {
  courseId: string
  conceptId: string
}

interface SSEStreamEvent {
  type: 'delta' | 'done' | 'error'
  text?: string
  tokens_in?: number
  tokens_out?: number
  cache_read?: number
  message?: string
}

type Phase = 'creating' | 'opening' | 'idle' | 'streaming' | 'ended' | 'error'

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

export function CoachingSession({ courseId, conceptId }: Props) {
  const [turns, setTurns] = useState<Turn[]>([])
  const [streamingText, setStreamingText] = useState<string>('')
  const [phase, setPhase] = useState<Phase>('creating')
  const [error, setError] = useState<string | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [concept, setConcept] = useState<ConceptInfo>({ id: conceptId })
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

  const streamTurn = useCallback(
    async (sid: string, userMessage: string) => {
      setPhase('streaming')
      setStreamingText('')
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
    },
    []
  )

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
        // Append empty user-turn placeholder? No — opening shows only the assistant
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

  const handleEnd = useCallback(async () => {
    if (!sessionId) return
    try {
      const r = await fetch(`/api/coaching/sessions/${sessionId}/end`, { method: 'POST' })
      if (r.ok) {
        const data = await r.json()
        setEndStats({ duration_min: data.duration_min, turn_count: data.turn_count })
        setPhase('ended')
      }
    } catch {
      // best effort
    }
  }, [sessionId])

  const turnCount = turns.filter((t) => t.role === 'assistant').length + (streamingText ? 1 : 0)
  const conceptLabel = concept.name ?? concept.id
  const isStreaming = phase === 'streaming' || phase === 'opening'

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
        <div className="flex items-baseline gap-3">
          <span className="text-gray-900 font-semibold">Coaching · {conceptLabel}</span>
          <span className="text-sm text-gray-500">{turnCount} Turns</span>
        </div>
        {phase !== 'ended' && (
          <button
            onClick={handleEnd}
            className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50"
          >
            Ende
          </button>
        )}
      </header>

      {/* Chat area */}
      <main className="flex-1 overflow-y-auto px-6 py-6">
        <div className="max-w-3xl mx-auto flex flex-col gap-6">
          {turns.map((t, i) => (
            <ChatTurn key={i} turn={t} />
          ))}

          {streamingText && (
            <ChatTurn
              turn={{ role: 'assistant', content: streamingText }}
              streaming
            />
          )}

          {phase === 'creating' && (
            <p className="text-gray-400 text-center">Session wird gestartet …</p>
          )}

          {phase === 'ended' && endStats && (
            <div className="text-center py-4 border-t border-gray-200">
              <p className="text-gray-700 font-medium">Session beendet</p>
              <p className="text-sm text-gray-500 mt-1">
                {endStats.turn_count} Turns · {endStats.duration_min.toFixed(1)} min
              </p>
            </div>
          )}

          {error && (
            <div role="alert" className="px-4 py-3 bg-red-50 border border-red-200 text-red-700 rounded-lg">
              {error}
            </div>
          )}

          <div ref={turnsEndRef} />
        </div>
      </main>

      {/* Input */}
      {phase !== 'ended' && (
        <footer className="px-6 py-4 border-t border-gray-200 bg-white">
          <div className="max-w-3xl mx-auto">
            <ChatInput onSend={handleSend} disabled={isStreaming || phase === 'creating' || phase === 'error'} />
          </div>
        </footer>
      )}
    </div>
  )
}
