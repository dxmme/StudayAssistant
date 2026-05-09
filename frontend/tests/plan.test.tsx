import { render, screen, fireEvent, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { PlanDashboard } from '@/components/PlanDashboard'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
}))

const MOCK_COURSES = [{ id: 'course-1', name: 'Statistical ML', exam_date: null }]

const MOCK_PLAN = {
  id: 'plan-1',
  course_id: 'course-1',
  scheduled_date: '2026-05-09',
  duration_min: 25,
  items: [
    {
      type: 'card_review',
      title: '5 fällige Karten',
      estimated_min: 10,
      done: false,
      concept_id: null,
      card_count: 5,
    },
    {
      type: 'new_concept',
      title: 'SVD',
      estimated_min: 10,
      done: false,
      concept_id: 'c-1',
      card_count: null,
    },
  ],
  status: 'pending',
  completed_at: null,
}

function mockFetch(overrides: Record<string, unknown> = {}) {
  let callCount = 0
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, opts?: { method?: string }) => {
      callCount++
      const method = opts?.method ?? 'GET'

      if (method === 'GET' && String(url).includes('/api/courses')) {
        return { ok: true, json: async () => MOCK_COURSES }
      }
      if (method === 'POST' && String(url).includes('/plan/today')) {
        return { ok: true, json: async () => ({ ...MOCK_PLAN, ...overrides }) }
      }
      if (method === 'PATCH' && String(url).includes('/items/')) {
        const updated = {
          ...MOCK_PLAN,
          items: MOCK_PLAN.items.map((item, i) => (i === 0 ? { ...item, done: true } : item)),
        }
        return { ok: true, json: async () => updated }
      }
      if (method === 'POST' && String(url).includes('/complete')) {
        return { ok: true, json: async () => ({ ...MOCK_PLAN, status: 'completed', completed_at: '2026-05-09T20:00:00Z' }) }
      }
      return { ok: false, json: async () => ({}) }
    })
  )
  return { getCallCount: () => callCount }
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: false })
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('PlanDashboard', () => {
  it('renders loading state before fetch resolves', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))
    render(<PlanDashboard />)
    expect(screen.getByText('Lade Pläne…')).toBeTruthy()
  })

  it('renders plan items after fetch', async () => {
    mockFetch()
    render(<PlanDashboard />)

    await act(async () => {
      await vi.runAllTimersAsync()
    })

    expect(screen.getByText(/5 fällige Karten/)).toBeTruthy()
    expect(screen.getByText(/SVD/)).toBeTruthy()
  })

  it('calls PATCH when checkbox is clicked', async () => {
    const fetchMock = vi.fn(async (url: string, opts?: { method?: string }) => {
      const method = opts?.method ?? 'GET'
      if (method === 'GET') return { ok: true, json: async () => MOCK_COURSES }
      if (method === 'POST' && String(url).includes('/plan/today')) {
        return { ok: true, json: async () => MOCK_PLAN }
      }
      if (method === 'PATCH') {
        return {
          ok: true,
          json: async () => ({
            ...MOCK_PLAN,
            items: MOCK_PLAN.items.map((item, i) => (i === 0 ? { ...item, done: true } : item)),
          }),
        }
      }
      return { ok: false, json: async () => ({}) }
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<PlanDashboard />)
    await act(async () => { await vi.runAllTimersAsync() })

    fireEvent.click(screen.getByTestId('item-checkbox-0'))
    await act(async () => { await vi.runAllTimersAsync() })

    const patchCall = fetchMock.mock.calls.find(
      ([, opts]) => (opts as { method?: string })?.method === 'PATCH'
    )
    expect(patchCall).toBeTruthy()
  })

  it('calls POST /complete when session complete button clicked', async () => {
    const fetchMock = vi.fn(async (url: string, opts?: { method?: string }) => {
      const method = opts?.method ?? 'GET'
      if (method === 'GET') return { ok: true, json: async () => MOCK_COURSES }
      if (method === 'POST' && String(url).includes('/plan/today')) {
        return { ok: true, json: async () => MOCK_PLAN }
      }
      if (method === 'POST' && String(url).includes('/complete')) {
        return { ok: true, json: async () => ({ ...MOCK_PLAN, status: 'completed', completed_at: '2026-05-09T20:00:00Z' }) }
      }
      return { ok: false, json: async () => ({}) }
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<PlanDashboard />)
    await act(async () => { await vi.runAllTimersAsync() })

    fireEvent.click(screen.getByTestId('complete-button'))
    await act(async () => { await vi.runAllTimersAsync() })

    const completeCall = fetchMock.mock.calls.find(
      ([url, opts]) =>
        String(url).includes('/complete') &&
        (opts as { method?: string })?.method === 'POST'
    )
    expect(completeCall).toBeTruthy()
  })

  it('renders empty state when no items', async () => {
    mockFetch({ items: [], duration_min: 0 })
    render(<PlanDashboard />)

    await act(async () => {
      await vi.runAllTimersAsync()
    })

    expect(screen.getByText('Heute nichts fällig.')).toBeTruthy()
  })
})
