import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { SettingsForm } from '@/components/SettingsForm'

const MOCK_PREFS = {
  id: 'default',
  display_name: 'Dominique',
  weekly_availability_minutes: {
    mon: 120, tue: 120, wed: 120, thu: 120, fri: 120, sat: 0, sun: 0,
  },
  max_session_minutes: 90,
}

function setupFetch(patchResponse = MOCK_PREFS) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (_url: string, opts?: RequestInit) => {
      if (opts?.method === 'PATCH') {
        return { ok: true, json: async () => patchResponse } as Response
      }
      return { ok: true, json: async () => MOCK_PREFS } as Response
    }),
  )
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: false })
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})

describe('SettingsForm', () => {
  it('renders 7 day fields, name input, and max-session input', async () => {
    setupFetch()
    render(<SettingsForm />)
    await act(async () => { await vi.runAllTimersAsync() })

    expect(screen.getByLabelText('Verfügbarkeit Mo')).toBeTruthy()
    expect(screen.getByLabelText('Verfügbarkeit Di')).toBeTruthy()
    expect(screen.getByLabelText('Verfügbarkeit Mi')).toBeTruthy()
    expect(screen.getByLabelText('Verfügbarkeit Do')).toBeTruthy()
    expect(screen.getByLabelText('Verfügbarkeit Fr')).toBeTruthy()
    expect(screen.getByLabelText('Verfügbarkeit Sa')).toBeTruthy()
    expect(screen.getByLabelText('Verfügbarkeit So')).toBeTruthy()
    expect(screen.getByLabelText('Maximale Session-Dauer')).toBeTruthy()
    expect(screen.getByPlaceholderText('Dein Name')).toBeTruthy()
  })

  it('pre-fills fields with values from GET /me', async () => {
    setupFetch()
    render(<SettingsForm />)
    await act(async () => { await vi.runAllTimersAsync() })

    const nameInput = screen.getByPlaceholderText('Dein Name') as HTMLInputElement
    expect(nameInput.value).toBe('Dominique')

    const monInput = screen.getByLabelText('Verfügbarkeit Mo') as HTMLInputElement
    expect(monInput.value).toBe('120')

    const maxInput = screen.getByLabelText('Maximale Session-Dauer') as HTMLInputElement
    expect(maxInput.value).toBe('90')
  })

  it('fires PATCH /me with updated data on submit', async () => {
    setupFetch()
    render(<SettingsForm />)
    await act(async () => { await vi.runAllTimersAsync() })

    const monInput = screen.getByLabelText('Verfügbarkeit Mo') as HTMLInputElement
    fireEvent.change(monInput, { target: { value: '180' } })

    const submitBtn = screen.getByRole('button', { name: /Speichern/i })
    await act(async () => { fireEvent.click(submitBtn) })
    await act(async () => { await vi.runAllTimersAsync() })

    const fetchMock = vi.mocked(fetch)
    const patchCall = fetchMock.mock.calls.find(
      ([, opts]) => (opts as RequestInit)?.method === 'PATCH',
    )
    expect(patchCall).toBeTruthy()
    const body = JSON.parse((patchCall![1] as RequestInit).body as string)
    expect(body.weekly_availability_minutes.mon).toBe(180)
  })
})
