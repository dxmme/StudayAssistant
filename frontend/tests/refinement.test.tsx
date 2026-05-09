import { render, screen, fireEvent, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { RefinementQueue } from '@/components/RefinementQueue'

vi.mock('@/components/MarkdownMath', () => ({
  MarkdownMath: ({ children }: { children: string }) => <span data-testid="markdown">{children}</span>,
}))

const PROPOSAL_ID = 'prop-001'
const CONCEPT_NAME = 'VC-Dimension'
const COURSE_NAME = 'Statistical ML'

function makeProposal(cardOverrides: Partial<{
  card_status: 'pending' | 'approved' | 'rejected'
}> = {}) {
  return {
    id: PROPOSAL_ID,
    concept_id: 'concept-1',
    concept_name: CONCEPT_NAME,
    course_name: COURSE_NAME,
    status: 'pending',
    again_count: 5,
    created_at: '2026-05-09T10:00:00',
    cards: [
      {
        index: 0,
        question: 'Was ist VC-Dim geometrisch?',
        answer: 'Die Anzahl shatter-barer Punkte.',
        rationale: 'Geometrische Perspektive',
        card_status: cardOverrides.card_status ?? 'pending',
      },
      {
        index: 1,
        question: 'Kontra-Beispiel VC-Dim?',
        answer: 'Kreis in ℝ² hat VC-Dim 3.',
        rationale: 'Gegenbeispiel',
        card_status: 'pending',
      },
    ],
  }
}

function setupFetch(options: {
  proposals?: object[]
  approveResponse?: object
  rejectResponse?: object
} = {}) {
  const proposals = options.proposals ?? [makeProposal()]
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, opts?: RequestInit) => {
      if (url.includes('/api/refinements') && (!opts || !opts.method)) {
        return { ok: true, json: async () => proposals } as Response
      }
      if (url.includes('/approve') && opts?.method === 'PATCH') {
        const proposal = { ...makeProposal({ card_status: 'approved' }), status: 'pending' }
        proposal.cards[0] = { ...proposal.cards[0], card_status: 'approved' }
        return { ok: true, json: async () => options.approveResponse ?? { proposal } } as Response
      }
      if (url.includes('/reject') && opts?.method === 'PATCH') {
        const proposal = makeProposal()
        proposal.cards[0] = { ...proposal.cards[0], card_status: 'rejected' }
        return { ok: true, json: async () => options.rejectResponse ?? { proposal } } as Response
      }
      return { ok: true, json: async () => ({}) } as Response
    })
  )
}

describe('RefinementQueue', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: false })
  })
  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('renders pending proposals', async () => {
    setupFetch()
    render(<RefinementQueue />)
    await act(async () => { await vi.runAllTimersAsync() })

    expect(screen.getByText(CONCEPT_NAME)).toBeTruthy()
    expect(screen.getByText(COURSE_NAME, { exact: false })).toBeTruthy()
    expect(screen.getByText('5× "Again" / 14d', { exact: false })).toBeTruthy()
    expect(screen.getByText('Was ist VC-Dim geometrisch?', { exact: false })).toBeTruthy()
  })

  it('shows empty state when no proposals', async () => {
    setupFetch({ proposals: [] })
    render(<RefinementQueue />)
    await act(async () => { await vi.runAllTimersAsync() })

    expect(screen.getByText('Keine offenen Refinements')).toBeTruthy()
  })

  it('approve calls PATCH endpoint', async () => {
    setupFetch()
    render(<RefinementQueue />)
    await act(async () => { await vi.runAllTimersAsync() })

    const approveButtons = screen.getAllByText('✓ Annehmen')
    await act(async () => {
      fireEvent.click(approveButtons[0])
      await vi.runAllTimersAsync()
    })

    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      `/api/refinements/${PROPOSAL_ID}/cards/0/approve`,
      expect.objectContaining({ method: 'PATCH' })
    )
  })

  it('reject calls PATCH endpoint', async () => {
    setupFetch()
    render(<RefinementQueue />)
    await act(async () => { await vi.runAllTimersAsync() })

    const rejectButtons = screen.getAllByText('✗ Ablehnen')
    await act(async () => {
      fireEvent.click(rejectButtons[0])
      await vi.runAllTimersAsync()
    })

    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      `/api/refinements/${PROPOSAL_ID}/cards/0/reject`,
      expect.objectContaining({ method: 'PATCH' })
    )
  })

  it('edit mode shows textareas for question and answer', async () => {
    setupFetch()
    render(<RefinementQueue />)
    await act(async () => { await vi.runAllTimersAsync() })

    const editButtons = screen.getAllByText('✎ Bearbeiten')
    fireEvent.click(editButtons[0])

    expect(screen.getByTestId('edit-question-0')).toBeTruthy()
    expect(screen.getByTestId('edit-answer-0')).toBeTruthy()
  })
})
