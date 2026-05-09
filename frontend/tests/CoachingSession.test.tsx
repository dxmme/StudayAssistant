import { render, screen, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { CoachingSession } from '@/components/CoachingSession'

// Mock MarkdownMath to avoid ESM transitive load + to make assertions easy.
vi.mock('@/components/MarkdownMath', () => ({
  MarkdownMath: ({ children }: { children: string }) => (
    <span data-testid="markdown-math">{children}</span>
  ),
}))

interface SSEEvent {
  type: 'delta' | 'done' | 'error'
  text?: string
  tokens_in?: number
  tokens_out?: number
  cache_read?: number
  message?: string
}

function makeSSEResponse(events: SSEEvent[]): Response {
  const encoder = new TextEncoder()
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const ev of events) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(ev)}\n\n`))
      }
      controller.close()
    },
  })
  return new Response(stream, {
    status: 200,
    headers: { 'Content-Type': 'text/event-stream' },
  })
}

interface ScriptedFetch {
  sessionId?: string
  openingDeltas?: string[]
  followUpDeltas?: string[]
  conceptName?: string
}

function setupScriptedFetch(scripted: ScriptedFetch) {
  let turnCallCount = 0
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const u = String(url)

      // GET concepts list
      if (u.endsWith('/concepts') && (!init || init.method !== 'POST')) {
        return {
          ok: true,
          json: async () => [{ id: 'k1', name: scripted.conceptName ?? 'SVD' }],
        } as Response
      }

      // POST /api/coaching/sessions
      if (u.endsWith('/api/coaching/sessions') && init?.method === 'POST') {
        return {
          ok: true,
          json: async () => ({
            session_id: scripted.sessionId ?? 'sess-123',
            started_at: new Date().toISOString(),
          }),
        } as Response
      }

      // POST /api/coaching/sessions/{id}/turn
      if (u.includes('/turn') && init?.method === 'POST') {
        turnCallCount += 1
        const deltas = turnCallCount === 1
          ? scripted.openingDeltas ?? ['Was ', 'ist ', 'SVD?']
          : scripted.followUpDeltas ?? ['Genau. ', 'Und warum?']
        return makeSSEResponse([
          ...deltas.map((text): SSEEvent => ({ type: 'delta', text })),
          { type: 'done', tokens_in: 100, tokens_out: 30, cache_read: 0 },
        ])
      }

      // POST /api/coaching/sessions/{id}/end
      if (u.includes('/end') && init?.method === 'POST') {
        return {
          ok: true,
          json: async () => ({ session_id: 'sess-123', duration_min: 12.5, turn_count: 2 }),
        } as Response
      }

      return { ok: false, status: 404, json: async () => ({}) } as Response
    })
  )
}

beforeEach(() => {
  // Use real timers so async streaming works naturally
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('CoachingSession', () => {
  it('creates session on mount and streams opening question delta-by-delta', async () => {
    setupScriptedFetch({ openingDeltas: ['Was ', 'unterscheidet ', 'SVD?'] })
    render(<CoachingSession courseId="c1" conceptId="k1" />)

    // After streaming completes, the assistant turn is rendered via MarkdownMath
    await waitFor(
      () => {
        const md = screen.queryAllByTestId('markdown-math')
        expect(md.some((n) => n.textContent === 'Was unterscheidet SVD?')).toBe(true)
      },
      { timeout: 2000 }
    )

    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/api/coaching/sessions',
      expect.objectContaining({ method: 'POST' })
    )
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/api/coaching/sessions/sess-123/turn',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('renders concept name in header (best-effort fetch)', async () => {
    setupScriptedFetch({ conceptName: 'Singular Value Decomposition' })
    render(<CoachingSession courseId="c1" conceptId="k1" />)

    await waitFor(() => {
      expect(screen.getByText(/Coaching · Singular Value Decomposition/)).toBeTruthy()
    })
  })

  it('user message via Enter triggers a follow-up turn', async () => {
    setupScriptedFetch({
      openingDeltas: ['Frage 1?'],
      followUpDeltas: ['Folge', 'frage'],
    })
    render(<CoachingSession courseId="c1" conceptId="k1" />)

    // Wait for opening to complete
    await waitFor(() => {
      const md = screen.queryAllByTestId('markdown-math')
      expect(md.some((n) => n.textContent === 'Frage 1?')).toBe(true)
    })

    // Find textarea, type, press Enter
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement
    await act(async () => {
      const ev = new Event('input', { bubbles: true })
      Object.defineProperty(ev, 'target', { value: { value: 'Meine Antwort' } })
      // simpler: directly set value via fireEvent
    })
    // Use direct value setter + dispatch
    const { fireEvent } = await import('@testing-library/react')
    fireEvent.change(textarea, { target: { value: 'Meine Antwort' } })
    fireEvent.keyDown(textarea, { key: 'Enter' })

    await waitFor(() => {
      const md = screen.queryAllByTestId('markdown-math')
      expect(md.some((n) => n.textContent === 'Folgefrage')).toBe(true)
    })

    // The user message should also be rendered (as a user turn — uses MarkdownMath)
    const md = screen.queryAllByTestId('markdown-math')
    expect(md.some((n) => n.textContent === 'Meine Antwort')).toBe(true)

    // Verify the POST included the user_message
    const turnCalls = vi.mocked(fetch).mock.calls.filter((c) =>
      String(c[0]).includes('/turn')
    )
    expect(turnCalls.length).toBe(2)
    const secondBody = JSON.parse(String(turnCalls[1][1]?.body))
    expect(secondBody.user_message).toBe('Meine Antwort')
  })

  it('Shift+Enter does NOT submit (allows newline)', async () => {
    setupScriptedFetch({})
    render(<CoachingSession courseId="c1" conceptId="k1" />)

    await waitFor(() => {
      expect(screen.queryAllByTestId('markdown-math').length).toBeGreaterThan(0)
    })

    const { fireEvent } = await import('@testing-library/react')
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement
    fireEvent.change(textarea, { target: { value: 'Erste Zeile' } })
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true })

    // Only the opening turn was a /turn request — no second one triggered
    const turnCalls = vi.mocked(fetch).mock.calls.filter((c) =>
      String(c[0]).includes('/turn')
    )
    expect(turnCalls.length).toBe(1)
  })

  it('End button calls end endpoint and hides input', async () => {
    setupScriptedFetch({})
    render(<CoachingSession courseId="c1" conceptId="k1" />)

    await waitFor(() => {
      expect(screen.queryAllByTestId('markdown-math').length).toBeGreaterThan(0)
    })

    const { fireEvent } = await import('@testing-library/react')
    fireEvent.click(screen.getByText('Ende'))

    await waitFor(() => {
      expect(screen.getByText('Session beendet')).toBeTruthy()
    })

    // Input should be gone
    expect(screen.queryByRole('textbox')).toBeNull()
  })
})
