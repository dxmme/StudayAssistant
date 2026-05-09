'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { MarkdownMath } from '@/components/MarkdownMath'

interface ProofTurn {
  turn_number: number
  user_proof: string
  llm_feedback: string
  steps_correct: number
  steps_total: number
  is_correct: boolean
}

interface TurnResponse {
  turn: ProofTurn
  turns_remaining: number
  is_finished: boolean
  final_rating: number | null
  credit_score: number | null
  reference_answer: string | null
}

interface Props {
  cardId: string
}

const MAX_TURNS = 5

export function ProofCheckerSession({ cardId }: Props) {
  const [attemptId, setAttemptId] = useState<string | null>(null)
  const [cardFront, setCardFront] = useState<string>('')
  const [turns, setTurns] = useState<ProofTurn[]>([])
  const [turnsRemaining, setTurnsRemaining] = useState(MAX_TURNS)
  const [userProof, setUserProof] = useState('')
  const [loading, setLoading] = useState(false)
  const [initError, setInitError] = useState<string | null>(null)
  const [finished, setFinished] = useState(false)
  const [finalRating, setFinalRating] = useState<number | null>(null)
  const [creditScore, setCreditScore] = useState<number | null>(null)
  const [referenceAnswer, setReferenceAnswer] = useState<string | null>(null)
  const [ratingApplied, setRatingApplied] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Load card + create attempt on mount
  useEffect(() => {
    async function init() {
      try {
        const cardRes = await fetch(`/api/cards/${cardId}`)
        if (!cardRes.ok) throw new Error('Card not found')
        const card = await cardRes.json() as { front: string }
        setCardFront(card.front)

        const attemptRes = await fetch(`/api/cards/${cardId}/proof-attempts`, { method: 'POST' })
        if (!attemptRes.ok) {
          const err = await attemptRes.json() as { detail: string }
          throw new Error(err.detail)
        }
        const attempt = await attemptRes.json() as { id: string }
        setAttemptId(attempt.id)
      } catch (e) {
        setInitError(e instanceof Error ? e.message : 'Fehler beim Laden.')
      }
    }
    void init()
  }, [cardId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ behavior: 'smooth' })
  }, [turns])

  const submitTurn = useCallback(async () => {
    if (!attemptId || !userProof.trim() || loading || finished) return
    setLoading(true)
    try {
      const res = await fetch(`/api/proof-attempts/${attemptId}/turns`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_proof: userProof }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json() as TurnResponse
      setTurns((prev) => [...prev, data.turn])
      setTurnsRemaining(data.turns_remaining)
      setUserProof('')
      if (data.is_finished) {
        setFinished(true)
        setFinalRating(data.final_rating)
        setCreditScore(data.credit_score)
        setReferenceAnswer(data.reference_answer)
      }
    } catch {
      // silent — keep state
    } finally {
      setLoading(false)
    }
  }, [attemptId, userProof, loading, finished])

  const applyRating = useCallback(async () => {
    if (!attemptId) return
    try {
      await fetch(`/api/proof-attempts/${attemptId}/apply-rating`, { method: 'PATCH' })
      setRatingApplied(true)
    } catch {
      // silent
    }
  }, [attemptId])

  const ratingLabel = (r: number) => ({ 1: 'Again', 2: 'Hard', 3: 'Good', 4: 'Easy' }[r] ?? '?')

  if (initError) {
    return (
      <div className="flex items-center justify-center min-h-screen text-red-600">
        {initError}
      </div>
    )
  }

  if (!attemptId) {
    return (
      <div className="flex items-center justify-center min-h-screen text-gray-400">
        Lade…
      </div>
    )
  }

  const currentTurn = turns.length + 1

  return (
    <div className="min-w-[640px] min-h-screen flex flex-col">
      <header className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
        <span className="text-gray-700 font-medium">Beweis-Rekonstruktion</span>
        {!finished && (
          <span className="text-gray-500 text-sm">Turn {currentTurn} / {MAX_TURNS}</span>
        )}
      </header>

      <main className="flex-1 px-6 py-6 max-w-3xl w-full mx-auto flex flex-col gap-6">
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Aufgabe</p>
          <MarkdownMath>{cardFront}</MarkdownMath>
        </div>

        {turns.length > 0 && (
          <div className="flex flex-col gap-4">
            {turns.map((t) => (
              <div key={t.turn_number} className="border border-gray-200 rounded-lg overflow-hidden">
                <div className="bg-gray-50 px-4 py-2 text-xs text-gray-500 font-medium">
                  Turn {t.turn_number} — Dein Beweis
                </div>
                <div className="px-4 py-3 font-mono text-sm whitespace-pre-wrap text-gray-800">
                  {t.user_proof}
                </div>
                <div className="bg-blue-50 px-4 py-3 border-t border-gray-200">
                  <p className="text-xs text-blue-600 font-medium mb-1">Feedback</p>
                  <MarkdownMath>{t.llm_feedback}</MarkdownMath>
                </div>
              </div>
            ))}
          </div>
        )}

        {!finished && (
          <div className="flex flex-col gap-3">
            <label className="text-sm text-gray-600 font-medium">Dein Beweis (Markdown + LaTeX):</label>
            <textarea
              value={userProof}
              onChange={(e) => setUserProof(e.target.value)}
              disabled={loading}
              rows={8}
              className="w-full font-mono text-sm border border-gray-300 rounded-lg p-3 resize-y focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-50"
              placeholder="Sei $n \in \mathbb{N}$. Dann gilt..."
            />
            {userProof.trim() && (
              <div className="border border-gray-200 rounded-lg p-3 bg-gray-50">
                <p className="text-xs text-gray-400 mb-2">Vorschau:</p>
                <MarkdownMath>{userProof}</MarkdownMath>
              </div>
            )}
            <button
              onClick={submitTurn}
              disabled={loading || !userProof.trim()}
              className="self-start px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Wird geprüft…' : 'Einreichen'}
            </button>
          </div>
        )}

        {finished && (
          <div className="border border-gray-200 rounded-lg p-5 flex flex-col gap-4">
            <div>
              <p className="text-sm text-gray-500 mb-1">Ergebnis</p>
              <p className="text-lg font-semibold text-gray-800">
                {creditScore !== null ? `${Math.round(creditScore * 100)}% korrekt` : '—'}
                {finalRating !== null && (
                  <span className="ml-3 text-base font-normal text-gray-500">
                    → Rating: {ratingLabel(finalRating)} ({finalRating})
                  </span>
                )}
              </p>
            </div>

            {referenceAnswer && (
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Musterantwort</p>
                <div className="bg-gray-50 border border-gray-200 rounded p-4">
                  <MarkdownMath>{referenceAnswer}</MarkdownMath>
                </div>
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={applyRating}
                disabled={ratingApplied}
                className="px-4 py-2 bg-violet-600 text-white rounded-lg text-sm font-medium hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {ratingApplied ? 'Rating übertragen ✓' : 'Rating auf Karte übertragen'}
              </button>
              <a
                href="/review"
                className="px-4 py-2 border border-gray-300 text-gray-600 rounded-lg text-sm font-medium hover:bg-gray-50"
              >
                Zurück zur Review
              </a>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </main>
    </div>
  )
}
