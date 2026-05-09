import { render, screen, act, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { WorkedExampleModal } from '@/components/WorkedExampleModal'
import { ReviewSession } from '@/components/ReviewSession'
import type { Card } from '@/types/card'

vi.mock('@/components/MarkdownMath', () => ({
  MarkdownMath: ({ children }: { children: string }) => <span data-testid="markdown">{children}</span>,
}))

// Also mock WorkedExampleModal in ReviewSession integration tests
// to avoid double-fetch complexity there
vi.mock('@/components/WorkedExampleModal', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/components/WorkedExampleModal')>()
  return actual  // use real implementation — MarkdownMath is already mocked
})

const EXAMPLE_CONTENT = '## Worked Example\n\n**Problem:** VC-Dim'

function setupModalFetch(ok = true) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (_url: string, opts?: RequestInit) => {
      if (opts?.method === 'POST') {
        if (!ok) throw new Error('Network error')
        return { ok: true, json: async () => ({ content: EXAMPLE_CONTENT }) } as Response
      }
      return { ok: true, json: async () => [] } as Response
    })
  )
}

function makeCard(id = 'c1'): Card {
  return {
    id,
    course_id: 'test-course',
    type: 'basic',
    front: 'Front Q',
    back: 'Back A',
    fsrs_state: { due: new Date().toISOString(), state: 1 },
    review_count: 0,
    lapse_count: 0,
    archived: false,
  }
}

function setupReviewFetch(cards: Card[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, opts?: RequestInit) => {
      if (url.includes('/worked-example')) {
        return { ok: true, json: async () => ({ content: EXAMPLE_CONTENT }) } as Response
      }
      if (!opts || opts.method !== 'POST') {
        return { ok: true, json: async () => cards } as Response
      }
      return { ok: true, json: async () => ({ card_id: cards[0]?.id, review_count: 1, lapse_count: 0 }) } as Response
    })
  )
}

function pressKey(code: string, key?: string) {
  window.dispatchEvent(new KeyboardEvent('keydown', { code, key: key ?? code, bubbles: true }))
}

// ── WorkedExampleModal unit tests ─────────────────────────────────────────────

describe('WorkedExampleModal', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: false })
  })
  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('shows spinner while loading', async () => {
    // fetch never resolves — stays loading
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))
    render(<WorkedExampleModal cardId="c1" onClose={vi.fn()} />)
    expect(screen.getByRole('status')).toBeTruthy()
  })

  it('renders content after successful fetch', async () => {
    setupModalFetch()
    render(<WorkedExampleModal cardId="c1" onClose={vi.fn()} />)
    await act(async () => { await vi.runAllTimersAsync() })
    expect(screen.getByTestId('markdown').textContent).toContain('Worked Example')
  })

  it('shows error message on fetch failure', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('fail') }))
    render(<WorkedExampleModal cardId="c1" onClose={vi.fn()} />)
    await act(async () => { await vi.runAllTimersAsync() })
    expect(screen.getByText(/konnte nicht geladen/)).toBeTruthy()
  })

  it('calls fetch POST /api/cards/{cardId}/worked-example on mount', async () => {
    setupModalFetch()
    render(<WorkedExampleModal cardId="my-card-id" onClose={vi.fn()} />)
    await act(async () => { await vi.runAllTimersAsync() })
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/api/cards/my-card-id/worked-example',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('calls onClose when × button is clicked', async () => {
    setupModalFetch()
    const onClose = vi.fn()
    render(<WorkedExampleModal cardId="c1" onClose={onClose} />)
    await act(async () => { await vi.runAllTimersAsync() })
    fireEvent.click(screen.getByRole('button', { name: /Schließen/ }))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('calls onClose when Escape key is pressed', async () => {
    setupModalFetch()
    const onClose = vi.fn()
    render(<WorkedExampleModal cardId="c1" onClose={onClose} />)
    await act(async () => { await vi.runAllTimersAsync() })
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    expect(onClose).toHaveBeenCalledOnce()
  })
})

// ── ReviewSession integration tests ───────────────────────────────────────────

describe('ReviewSession — Lösung anzeigen Button', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: false })
  })
  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('button not visible before card is flipped', async () => {
    setupReviewFetch([makeCard()])
    render(<ReviewSession courseId="test-course" />)
    await act(async () => { await vi.runAllTimersAsync() })

    expect(screen.queryByText('Lösung anzeigen')).toBeNull()
  })

  it('button visible after card is flipped', async () => {
    setupReviewFetch([makeCard()])
    render(<ReviewSession courseId="test-course" />)
    await act(async () => { await vi.runAllTimersAsync() })

    act(() => pressKey('Space'))
    expect(screen.getByText('Lösung anzeigen')).toBeTruthy()
  })

  it('clicking button opens modal and fetches worked example', async () => {
    setupReviewFetch([makeCard('card-42')])
    render(<ReviewSession courseId="test-course" />)
    await act(async () => { await vi.runAllTimersAsync() })

    act(() => pressKey('Space'))
    await act(async () => {
      fireEvent.click(screen.getByText('Lösung anzeigen'))
      await vi.runAllTimersAsync()
    })

    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/api/cards/card-42/worked-example',
      expect.objectContaining({ method: 'POST' })
    )
    expect(screen.getByRole('dialog')).toBeTruthy()
  })
})
