'use client'
import { useCallback, useEffect, useState } from 'react'
import { MarkdownMath } from './MarkdownMath'

export interface QuizQuestion {
  question: string
  options: string[]
  correct_index: number
  explanation: string
}

interface Props {
  quiz: QuizQuestion[]
  onComplete: () => void
  onSkip: () => void
}

export function CoachingQuiz({ quiz, onComplete, onSkip }: Props) {
  const [index, setIndex] = useState(0)
  const [selected, setSelected] = useState<number | null>(null)

  const q = quiz[index]
  const isLast = index >= quiz.length - 1

  const choose = useCallback(
    (i: number) => {
      setSelected((prev) => (prev === null ? i : prev))
    },
    []
  )

  const advance = useCallback(() => {
    if (isLast) {
      onComplete()
    } else {
      setIndex((i) => i + 1)
      setSelected(null)
    }
  }, [isLast, onComplete])

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (!q) return
      if (selected === null) {
        const n = Number(e.key)
        if (Number.isInteger(n) && n >= 1 && n <= q.options.length) {
          e.preventDefault()
          choose(n - 1)
        }
      } else if (e.key === 'Enter') {
        e.preventDefault()
        advance()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [q, selected, choose, advance])

  if (!q) return null

  const answered = selected !== null

  return (
    <div className="flex flex-col gap-6">
      <div
        className="rounded-2xl px-8 py-7"
        style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)' }}
      >
        <div className="flex items-baseline justify-between mb-3">
          <span
            className="text-[11px] font-medium uppercase tracking-[0.12em]"
            style={{ color: 'var(--text-muted)' }}
          >
            Verständnis-Check
          </span>
          <span className="text-xs tabular-nums" style={{ color: 'var(--text-muted)' }}>
            {index + 1} / {quiz.length}
          </span>
        </div>

        <div className="text-lg leading-relaxed font-medium" style={{ color: 'var(--text)' }}>
          <MarkdownMath>{q.question}</MarkdownMath>
        </div>

        <div className="mt-4 flex flex-col gap-2">
          {q.options.map((opt, i) => {
            const isCorrect = i === q.correct_index
            const isChosen = i === selected
            let border = 'var(--border)'
            let bg = 'var(--surface-2)'
            if (answered && isCorrect) {
              border = '#22c55e'
              bg = 'rgba(34,197,94,0.12)'
            } else if (answered && isChosen && !isCorrect) {
              border = '#ef4444'
              bg = 'rgba(239,68,68,0.12)'
            }
            return (
              <button
                key={i}
                onClick={() => choose(i)}
                disabled={answered}
                className="flex items-start gap-3 rounded-xl px-4 py-3 text-left text-sm transition-colors"
                style={{
                  backgroundColor: bg,
                  border: `1px solid ${border}`,
                  color: 'var(--text)',
                  cursor: answered ? 'default' : 'pointer',
                }}
              >
                <span
                  className="shrink-0 text-xs font-semibold mt-0.5"
                  style={{ color: 'var(--text-dim)' }}
                >
                  {i + 1}
                </span>
                <span className="flex-1">
                  <MarkdownMath>{opt}</MarkdownMath>
                </span>
              </button>
            )
          })}
        </div>

        {answered && (
          <div
            className="mt-4 rounded-xl px-4 py-3 text-sm leading-relaxed"
            style={{ backgroundColor: 'var(--surface-2)', border: '1px solid var(--border)' }}
          >
            <span
              className="font-semibold"
              style={{ color: selected === q.correct_index ? '#22c55e' : '#ef4444' }}
            >
              {selected === q.correct_index ? 'Richtig.' : 'Nicht ganz.'}
            </span>{' '}
            <span style={{ color: 'var(--text-muted)' }}>
              <MarkdownMath>{q.explanation}</MarkdownMath>
            </span>
          </div>
        )}
      </div>

      <div className="flex justify-center gap-3">
        <button
          onClick={onSkip}
          className="px-6 py-2.5 rounded-xl font-medium text-sm transition-colors"
          style={{ border: '1px solid var(--border)', color: 'var(--text-muted)' }}
        >
          Quiz überspringen
        </button>
        <button
          onClick={advance}
          disabled={!answered}
          className="px-7 py-2.5 rounded-xl font-medium text-sm transition-colors"
          style={{
            backgroundColor: 'var(--accent)',
            color: 'var(--bg)',
            opacity: answered ? 1 : 0.5,
            cursor: answered ? 'pointer' : 'not-allowed',
          }}
        >
          {isLast ? 'Abschließen' : 'Weiter →'}
        </button>
      </div>
    </div>
  )
}
