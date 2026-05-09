'use client'
import { useCallback, useEffect, useReducer } from 'react'
import { CardView } from './CardView'
import { RatingBar } from './RatingBar'
import type { Card } from '@/types/card'

interface Props {
  courseId: string
}

interface Stats {
  reviewed: number
  lapses: number
  ratingSum: number
}

type Phase = 'loading' | 'front' | 'back' | 'done' | 'empty'

interface State {
  cards: Card[]
  total: number
  currentIndex: number
  phase: Phase
  stats: Stats
  requestInFlight: boolean
  errorToast: string | null
}

type Action =
  | { type: 'LOADED'; cards: Card[] }
  | { type: 'FLIP' }
  | { type: 'RATING_START' }
  | { type: 'RATING_DONE'; wasLapse: boolean; rating: number }
  | { type: 'RATING_ERROR'; message: string }
  | { type: 'DISMISS_TOAST' }

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'LOADED':
      if (action.cards.length === 0) {
        return { ...state, cards: [], total: 0, phase: 'empty' }
      }
      return { ...state, cards: action.cards, total: action.cards.length, phase: 'front' }

    case 'FLIP':
      if (state.phase !== 'front') return state
      return { ...state, phase: 'back' }

    case 'RATING_START':
      return { ...state, requestInFlight: true }

    case 'RATING_DONE': {
      const stats: Stats = {
        reviewed: state.stats.reviewed + 1,
        lapses: state.stats.lapses + (action.wasLapse ? 1 : 0),
        ratingSum: state.stats.ratingSum + action.rating,
      }
      const nextIndex = state.currentIndex + 1
      if (nextIndex >= state.cards.length) {
        return { ...state, stats, requestInFlight: false, phase: 'done' }
      }
      return { ...state, stats, currentIndex: nextIndex, phase: 'front', requestInFlight: false }
    }

    case 'RATING_ERROR':
      return { ...state, requestInFlight: false, errorToast: action.message, phase: 'back' }

    case 'DISMISS_TOAST':
      return { ...state, errorToast: null }
  }
}

const INITIAL: State = {
  cards: [],
  total: 0,
  currentIndex: 0,
  phase: 'loading',
  stats: { reviewed: 0, lapses: 0, ratingSum: 0 },
  requestInFlight: false,
  errorToast: null,
}

export function ReviewSession({ courseId }: Props) {
  const [state, dispatch] = useReducer(reducer, INITIAL)

  useEffect(() => {
    fetch(`/api/courses/${courseId}/cards/due`)
      .then((r) => r.json())
      .then((cards: Card[]) => dispatch({ type: 'LOADED', cards }))
      .catch(() => dispatch({ type: 'LOADED', cards: [] }))
  }, [courseId])

  const submitRating = useCallback(
    async (rating: number) => {
      if (state.requestInFlight) return
      const card = state.cards[state.currentIndex]
      if (!card) return
      dispatch({ type: 'RATING_START' })
      try {
        const r = await fetch(`/api/cards/${card.id}/review`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ rating }),
        })
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        dispatch({ type: 'RATING_DONE', wasLapse: rating === 1, rating })
      } catch {
        dispatch({ type: 'RATING_ERROR', message: 'Netzwerkfehler — bitte nochmal versuchen.' })
      }
    },
    [state.requestInFlight, state.cards, state.currentIndex]
  )

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (state.phase === 'front' && e.code === 'Space') {
        e.preventDefault()
        dispatch({ type: 'FLIP' })
        return
      }
      if (state.phase === 'back' && !state.requestInFlight) {
        const rating = parseInt(e.key, 10)
        if (rating >= 1 && rating <= 4) {
          submitRating(rating)
        }
      }
      if (state.errorToast && e.code === 'Escape') {
        dispatch({ type: 'DISMISS_TOAST' })
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [state.phase, state.requestInFlight, state.errorToast, submitRating])

  if (state.phase === 'loading') {
    return (
      <div className="flex items-center justify-center min-h-screen text-gray-400">
        Lade Karten…
      </div>
    )
  }

  if (state.phase === 'empty' || state.phase === 'done') {
    const avgRating =
      state.stats.reviewed > 0
        ? (state.stats.ratingSum / state.stats.reviewed).toFixed(1)
        : '—'
    const heading = state.phase === 'empty' ? 'Keine Karten fällig' : 'Heute fertig'

    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center max-w-md px-6">
          <h1 className="text-3xl font-bold mb-6">{heading}</h1>
          {state.stats.reviewed > 0 && (
            <div className="space-y-2 text-gray-600">
              <p>
                Reviewed: <strong>{state.stats.reviewed}</strong>
              </p>
              <p>
                Lapses: <strong>{state.stats.lapses}</strong>
              </p>
              <p>
                Ø Rating: <strong>{avgRating}</strong>
              </p>
            </div>
          )}
        </div>
      </div>
    )
  }

  const card = state.cards[state.currentIndex]
  if (!card) return null
  const flipped = state.phase === 'back'

  return (
    <div className="min-w-[640px] min-h-screen flex flex-col">
      <header className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
        <span className="text-gray-700 font-medium">Review · {courseId}</span>
        <span className="text-gray-500 text-sm">
          {state.currentIndex + 1} / {state.total}
        </span>
      </header>

      <main className="flex-1 flex items-start justify-center px-6 py-8">
        <div className="w-full max-w-3xl">
          <CardView card={card} flipped={flipped} />
        </div>
      </main>

      <footer className="px-6 py-4 border-t border-gray-200 flex justify-center">
        <RatingBar flipped={flipped} disabled={state.requestInFlight} />
      </footer>

      {state.errorToast && (
        <div
          role="alert"
          className="fixed bottom-4 right-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg shadow-md flex items-center gap-3"
        >
          <span>{state.errorToast}</span>
          <button
            onClick={() => dispatch({ type: 'DISMISS_TOAST' })}
            className="text-red-500 hover:text-red-700"
            aria-label="Schließen"
          >
            ✕
          </button>
        </div>
      )}
    </div>
  )
}
