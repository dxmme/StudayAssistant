import { render, screen, act, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ProofCheckerSession } from '@/components/ProofCheckerSession'

vi.mock('@/components/MarkdownMath', () => ({
  MarkdownMath: ({ children }: { children: string }) => <span data-testid="markdown">{children}</span>,
}))

const CARD_ID = 'card-proof-1'
const ATTEMPT_ID = 'attempt-001'
const CARD_FRONT = 'Zeige, dass die VC-Dim. des Halbraums in ℝᵈ gleich d+1 ist.'

function makeTurnResponse(override: Partial<{
  turn_number: number
  is_correct: boolean
  is_finished: boolean
  final_rating: number | null
  credit_score: number | null
  reference_answer: string | null
  turns_remaining: number
}> = {}) {
  return {
    turn: {
      turn_number: override.turn_number ?? 1,
      user_proof: 'Mein Beweis...',
      llm_feedback: 'Korrekt bis Schritt 2. Fehler: ...\nSTEPS_CORRECT: 2, STEPS_TOTAL: 4',
      steps_correct: 2,
      steps_total: 4,
      is_correct: override.is_correct ?? false,
    },
    turns_remaining: override.turns_remaining ?? 4,
    is_finished: override.is_finished ?? false,
    final_rating: override.final_rating ?? null,
    credit_score: override.credit_score ?? null,
    reference_answer: override.reference_answer ?? null,
  }
}

function setupFetch(options: { turnResponse?: object; finishOnTurn?: boolean } = {}) {
  let turnCount = 0
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, opts?: RequestInit) => {
      if (url.includes(`/api/cards/${CARD_ID}`) && !url.includes('proof-attempts') && (!opts || opts.method !== 'POST')) {
        return { ok: true, json: async () => ({ id: CARD_ID, front: CARD_FRONT, proof_mode: true }) } as Response
      }
      if (url.includes('proof-attempts') && opts?.method === 'POST' && !url.includes('turns')) {
        return { ok: true, json: async () => ({ id: ATTEMPT_ID, card_id: CARD_ID, turns: [] }) } as Response
      }
      if (url.includes('turns') && opts?.method === 'POST') {
        turnCount++
        const isFinished = options.finishOnTurn ? turnCount >= options.finishOnTurn : false
        const resp = options.turnResponse ?? makeTurnResponse({
          turn_number: turnCount,
          is_finished: isFinished,
          final_rating: isFinished ? 4 : null,
          credit_score: isFinished ? 1.0 : null,
          reference_answer: isFinished ? 'Musterantwort hier.' : null,
          turns_remaining: Math.max(0, 5 - turnCount),
        })
        return { ok: true, json: async () => resp } as Response
      }
      if (url.includes('apply-rating') && opts?.method === 'PATCH') {
        return { ok: true, json: async () => ({ card_id: CARD_ID, applied_rating: 4, new_fsrs_state: {} }) } as Response
      }
      return { ok: true, json: async () => ({}) } as Response
    })
  )
}

describe('ProofCheckerSession', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: false })
  })
  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('renders task and textarea after init', async () => {
    setupFetch()
    render(<ProofCheckerSession cardId={CARD_ID} />)
    await act(async () => { await vi.runAllTimersAsync() })

    expect(screen.getByText(CARD_FRONT)).toBeTruthy()
    expect(screen.getByPlaceholderText(/Sei/)).toBeTruthy()
  })

  it('submit button calls POST turns API', async () => {
    setupFetch()
    render(<ProofCheckerSession cardId={CARD_ID} />)
    await act(async () => { await vi.runAllTimersAsync() })

    fireEvent.change(screen.getByPlaceholderText(/Sei/), { target: { value: 'Mein Beweis' } })
    await act(async () => {
      fireEvent.click(screen.getByText('Einreichen'))
      await vi.runAllTimersAsync()
    })

    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      `/api/proof-attempts/${ATTEMPT_ID}/turns`,
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('renders feedback in MarkdownMath after submit', async () => {
    setupFetch()
    render(<ProofCheckerSession cardId={CARD_ID} />)
    await act(async () => { await vi.runAllTimersAsync() })

    fireEvent.change(screen.getByPlaceholderText(/Sei/), { target: { value: 'Mein Beweis' } })
    await act(async () => {
      fireEvent.click(screen.getByText('Einreichen'))
      await vi.runAllTimersAsync()
    })

    const markdownEls = screen.getAllByTestId('markdown')
    const hasFeeback = markdownEls.some((el) => el.textContent?.includes('STEPS_CORRECT'))
    expect(hasFeeback).toBe(true)
  })

  it('turn counter updates after submit', async () => {
    setupFetch()
    render(<ProofCheckerSession cardId={CARD_ID} />)
    await act(async () => { await vi.runAllTimersAsync() })

    expect(screen.getByText('Turn 1 / 5')).toBeTruthy()

    fireEvent.change(screen.getByPlaceholderText(/Sei/), { target: { value: 'Mein Beweis' } })
    await act(async () => {
      fireEvent.click(screen.getByText('Einreichen'))
      await vi.runAllTimersAsync()
    })

    expect(screen.getByText('Turn 2 / 5')).toBeTruthy()
  })

  it('shows reference answer when finished', async () => {
    setupFetch({ finishOnTurn: 1 })
    render(<ProofCheckerSession cardId={CARD_ID} />)
    await act(async () => { await vi.runAllTimersAsync() })

    fireEvent.change(screen.getByPlaceholderText(/Sei/), { target: { value: 'Korrekter Beweis' } })
    await act(async () => {
      fireEvent.click(screen.getByText('Einreichen'))
      await vi.runAllTimersAsync()
    })

    expect(screen.getByText('Musterantwort hier.')).toBeTruthy()
    expect(screen.getByText('Rating auf Karte übertragen')).toBeTruthy()
  })

  it('apply-rating button calls PATCH endpoint', async () => {
    setupFetch({ finishOnTurn: 1 })
    render(<ProofCheckerSession cardId={CARD_ID} />)
    await act(async () => { await vi.runAllTimersAsync() })

    fireEvent.change(screen.getByPlaceholderText(/Sei/), { target: { value: 'Beweis' } })
    await act(async () => {
      fireEvent.click(screen.getByText('Einreichen'))
      await vi.runAllTimersAsync()
    })

    await act(async () => {
      fireEvent.click(screen.getByText('Rating auf Karte übertragen'))
      await vi.runAllTimersAsync()
    })

    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      `/api/proof-attempts/${ATTEMPT_ID}/apply-rating`,
      expect.objectContaining({ method: 'PATCH' })
    )
    expect(screen.getByText('Rating übertragen ✓')).toBeTruthy()
  })
})
