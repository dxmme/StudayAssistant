import { render, screen, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ReviewSession } from '@/components/ReviewSession'
import type { Card } from '@/types/card'

// Mock MarkdownMath to avoid ESM dependency chain in unit tests
vi.mock('@/components/MarkdownMath', () => ({
  MarkdownMath: ({ children }: { children: string }) => <span>{children}</span>,
}))

function makeCard(id: string, front: string, back: string): Card {
  return {
    id,
    course_id: 'test-course',
    type: 'basic',
    front,
    back,
    fsrs_state: { due: new Date().toISOString(), state: 1 },
    review_count: 0,
    lapse_count: 0,
    archived: false,
  }
}

const CARDS: Card[] = [
  makeCard('c1', 'Front 1', 'Back 1'),
  makeCard('c2', 'Front 2', 'Back 2'),
  makeCard('c3', 'Front 3', 'Back 3'),
]

const REVIEW_RESPONSE = {
  card_id: 'c1',
  fsrs_state: { due: new Date().toISOString() },
  next_due: new Date().toISOString(),
  lapse_count: 0,
  review_count: 1,
}

function setupFetch(cards: Card[]) {
  let callCount = 0
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, opts?: RequestInit) => {
      if (!opts || opts.method !== 'POST') {
        // GET /api/courses/.../cards/due
        return { ok: true, json: async () => cards } as Response
      }
      // POST /api/cards/.../review
      callCount++
      return { ok: true, json: async () => ({ ...REVIEW_RESPONSE, review_count: callCount }) } as Response
    })
  )
}

function pressKey(code: string, key?: string) {
  window.dispatchEvent(new KeyboardEvent('keydown', { code, key: key ?? code, bubbles: true }))
}

describe('ReviewSession', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: false })
  })
  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('shows loading, then first card in front state', async () => {
    setupFetch(CARDS)
    render(<ReviewSession courseId="test-course" />)

    expect(screen.getByText('Lade Karten…')).toBeTruthy()

    await act(async () => {
      await vi.runAllTimersAsync()
    })

    expect(screen.getByText('Front 1')).toBeTruthy()
    expect(screen.queryByText('Back 1')).toBeNull()
  })

  it('Space flips card to back state — shows both front and back', async () => {
    setupFetch(CARDS)
    render(<ReviewSession courseId="test-course" />)
    await act(async () => { await vi.runAllTimersAsync() })

    expect(screen.queryByText('Back 1')).toBeNull()

    act(() => pressKey('Space'))

    expect(screen.getByText('Front 1')).toBeTruthy()
    expect(screen.getByText('Back 1')).toBeTruthy()
  })

  it('pressing 3 after flip posts review and advances to next card', async () => {
    setupFetch(CARDS)
    render(<ReviewSession courseId="test-course" />)
    await act(async () => { await vi.runAllTimersAsync() })

    act(() => pressKey('Space'))
    await act(async () => {
      pressKey('Digit3', '3')
      await vi.runAllTimersAsync()
    })

    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/api/cards/c1/review',
      expect.objectContaining({ method: 'POST' })
    )
    expect(screen.getByText('Front 2')).toBeTruthy()
    expect(screen.queryByText('Back 2')).toBeNull()
    // counter shows 2/3
    expect(screen.getByText('2 / 3')).toBeTruthy()
  })

  it('rating last card shows empty state with stats', async () => {
    setupFetch([makeCard('only', 'Q', 'A')])
    render(<ReviewSession courseId="test-course" />)
    await act(async () => { await vi.runAllTimersAsync() })

    act(() => pressKey('Space'))
    await act(async () => {
      pressKey('Digit3', '3')
      await vi.runAllTimersAsync()
    })

    expect(screen.getByText('Heute fertig')).toBeTruthy()
    expect(screen.getByText(/Reviewed:/)).toBeTruthy()
  })

  it('empty course shows empty state immediately', async () => {
    setupFetch([])
    render(<ReviewSession courseId="test-course" />)
    await act(async () => { await vi.runAllTimersAsync() })

    expect(screen.getByText('Keine Karten fällig')).toBeTruthy()
  })

  it('rating 1 (Again) increments lapse count in stats', async () => {
    const card = makeCard('lapse-card', 'Q', 'A')
    setupFetch([card])
    render(<ReviewSession courseId="test-course" />)
    await act(async () => { await vi.runAllTimersAsync() })

    act(() => pressKey('Space'))
    await act(async () => {
      pressKey('Digit1', '1')
      await vi.runAllTimersAsync()
    })

    expect(screen.getByText('Heute fertig')).toBeTruthy()
    expect(screen.getByText(/Lapses:/).textContent).toContain('1')
  })

  it('shows error toast on network failure and stays in back state', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, opts?: RequestInit) => {
        if (!opts || opts.method !== 'POST') {
          return { ok: true, json: async () => CARDS } as Response
        }
        throw new Error('Network error')
      })
    )
    render(<ReviewSession courseId="test-course" />)
    await act(async () => { await vi.runAllTimersAsync() })

    act(() => pressKey('Space'))
    await act(async () => {
      pressKey('Digit3', '3')
      await vi.runAllTimersAsync()
    })

    expect(screen.getByRole('alert')).toBeTruthy()
    // still on card 1
    expect(screen.getByText('Front 1')).toBeTruthy()
  })
})
