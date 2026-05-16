import { render, screen, waitFor, act, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, afterEach } from 'vitest'
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
  ready?: boolean
  tokens_in?: number
  tokens_out?: number
  cache_read?: number
  message?: string
}

interface QuizQuestion {
  question: string
  options: string[]
  correct_index: number
  explanation: string
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
  doneReady?: boolean
  endSummary?: string | null
  endQuiz?: QuizQuestion[]
}

function setupScriptedFetch(scripted: ScriptedFetch) {
  let turnCallCount = 0
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const u = String(url)

      if (u.endsWith('/concepts') && (!init || init.method !== 'POST')) {
        return {
          ok: true,
          json: async () => [{ id: 'k1', name: scripted.conceptName ?? 'SVD' }],
        } as Response
      }

      if (u.endsWith('/api/coaching/sessions') && init?.method === 'POST') {
        return {
          ok: true,
          json: async () => ({
            session_id: scripted.sessionId ?? 'sess-123',
            started_at: new Date().toISOString(),
          }),
        } as Response
      }

      if (u.includes('/turn') && init?.method === 'POST') {
        turnCallCount += 1
        const deltas =
          turnCallCount === 1
            ? scripted.openingDeltas ?? ['Was ', 'ist ', 'SVD?']
            : scripted.followUpDeltas ?? ['Genau. ', 'Und warum?']
        return makeSSEResponse([
          ...deltas.map((text): SSEEvent => ({ type: 'delta', text })),
          {
            type: 'done',
            ready: scripted.doneReady ?? false,
            tokens_in: 100,
            tokens_out: 30,
            cache_read: 0,
          },
        ])
      }

      if (u.includes('/end') && init?.method === 'POST') {
        return {
          ok: true,
          json: async () => ({
            session_id: 'sess-123',
            duration_min: 12.5,
            turn_count: 2,
            summary: scripted.endSummary === undefined ? 'Test-Zusammenfassung.' : scripted.endSummary,
            quiz: scripted.endQuiz ?? [],
          }),
        } as Response
      }

      return { ok: false, status: 404, json: async () => ({}) } as Response
    })
  )
}

const SAMPLE_QUIZ: QuizQuestion[] = [
  {
    question: 'Quizfrage A?',
    options: ['Antwort 1', 'Antwort 2'],
    correct_index: 0,
    explanation: 'Erklärung dazu.',
  },
]

async function renderToIdle(props?: Partial<{ onEnd: () => void }>) {
  render(<CoachingSession courseId="c1" conceptId="k1" onEnd={props?.onEnd} />)
  await waitFor(() => {
    expect(screen.queryAllByTestId('markdown-math').length).toBeGreaterThan(0)
  })
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('CoachingSession — chat', () => {
  it('creates session on mount and streams the opening question delta-by-delta', async () => {
    setupScriptedFetch({ openingDeltas: ['Was ', 'unterscheidet ', 'SVD?'] })
    render(<CoachingSession courseId="c1" conceptId="k1" />)

    await waitFor(() => {
      const md = screen.queryAllByTestId('markdown-math')
      expect(md.some((n) => n.textContent === 'Was unterscheidet SVD?')).toBe(true)
    })

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
    setupScriptedFetch({ openingDeltas: ['Frage 1?'], followUpDeltas: ['Folge', 'frage'] })
    render(<CoachingSession courseId="c1" conceptId="k1" />)

    await waitFor(() => {
      const md = screen.queryAllByTestId('markdown-math')
      expect(md.some((n) => n.textContent === 'Frage 1?')).toBe(true)
    })

    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement
    fireEvent.change(textarea, { target: { value: 'Meine Antwort' } })
    fireEvent.keyDown(textarea, { key: 'Enter' })

    await waitFor(() => {
      const md = screen.queryAllByTestId('markdown-math')
      expect(md.some((n) => n.textContent === 'Folgefrage')).toBe(true)
    })

    const md = screen.queryAllByTestId('markdown-math')
    expect(md.some((n) => n.textContent === 'Meine Antwort')).toBe(true)

    const turnCalls = vi.mocked(fetch).mock.calls.filter((c) => String(c[0]).includes('/turn'))
    expect(turnCalls.length).toBe(2)
    const secondBody = JSON.parse(String(turnCalls[1]?.[1]?.body))
    expect(secondBody.user_message).toBe('Meine Antwort')
  })

  it('Shift+Enter does NOT submit (allows newline)', async () => {
    setupScriptedFetch({})
    render(<CoachingSession courseId="c1" conceptId="k1" />)

    await waitFor(() => {
      expect(screen.queryAllByTestId('markdown-math').length).toBeGreaterThan(0)
    })

    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement
    fireEvent.change(textarea, { target: { value: 'Erste Zeile' } })
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true })

    const turnCalls = vi.mocked(fetch).mock.calls.filter((c) => String(c[0]).includes('/turn'))
    expect(turnCalls.length).toBe(1)
  })
})

describe('CoachingSession — conclusion flow', () => {
  it('highlights the End button when the coach signals readiness', async () => {
    setupScriptedFetch({ doneReady: true })
    render(<CoachingSession courseId="c1" conceptId="k1" />)
    await waitFor(() => {
      expect(screen.getByText('Konzept verstanden — beenden')).toBeTruthy()
    })
  })

  it('End button opens the summary screen and hides the input', async () => {
    setupScriptedFetch({ endSummary: 'Die SVD zerlegt eine Matrix.' })
    await renderToIdle()

    await act(async () => {
      fireEvent.click(screen.getByText('Ende'))
    })

    await waitFor(() => {
      expect(screen.getByText('Die SVD zerlegt eine Matrix.')).toBeTruthy()
    })
    expect(screen.queryByRole('textbox')).toBeNull()
  })

  it('quiz: pressing key 1 selects the first option and shows feedback', async () => {
    setupScriptedFetch({ endSummary: 'Recap.', endQuiz: SAMPLE_QUIZ })
    await renderToIdle()

    await act(async () => {
      fireEvent.click(screen.getByText('Ende'))
    })
    await waitFor(() => screen.getByText('Zum Quiz →'))
    fireEvent.click(screen.getByText('Zum Quiz →'))
    await waitFor(() => screen.getByText('Quizfrage A?'))

    act(() => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: '1', bubbles: true }))
    })

    expect(screen.getByText('Richtig.')).toBeTruthy()
    expect(screen.getByText('Erklärung dazu.')).toBeTruthy()
  })

  it('Überspringen on the summary screen completes the session and fires onEnd', async () => {
    const onEnd = vi.fn()
    setupScriptedFetch({ endSummary: 'Recap.', endQuiz: SAMPLE_QUIZ })
    await renderToIdle({ onEnd })

    await act(async () => {
      fireEvent.click(screen.getByText('Ende'))
    })
    await waitFor(() => screen.getByText('Überspringen'))
    fireEvent.click(screen.getByText('Überspringen'))

    expect(screen.getByText('Session abgeschlossen')).toBeTruthy()
    expect(onEnd).toHaveBeenCalledOnce()
  })

  it('shows an error hint when the summary could not be generated', async () => {
    setupScriptedFetch({ endSummary: null, endQuiz: [] })
    await renderToIdle()

    await act(async () => {
      fireEvent.click(screen.getByText('Ende'))
    })

    await waitFor(() => {
      expect(screen.getByText('Die Zusammenfassung konnte nicht erstellt werden.')).toBeTruthy()
    })
  })
})
