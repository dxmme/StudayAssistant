'use client'
import { MarkdownMath } from './MarkdownMath'

interface Action {
  label: string
  onClick: () => void
}

interface Props {
  summary: string | null
  primary: Action
  secondary?: Action
}

export function CoachingSummary({ summary, primary, secondary }: Props) {
  return (
    <div className="flex flex-col gap-6">
      <div
        className="rounded-2xl px-8 py-7"
        style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)' }}
      >
        <span
          className="text-[11px] font-medium uppercase tracking-[0.12em] block mb-3"
          style={{ color: 'var(--text-muted)' }}
        >
          Zusammenfassung
        </span>
        {summary ? (
          <div className="text-sm leading-relaxed" style={{ color: 'var(--text)' }}>
            <MarkdownMath>{summary}</MarkdownMath>
          </div>
        ) : (
          <p className="text-sm" style={{ color: '#fca5a5' }}>
            Die Zusammenfassung konnte nicht erstellt werden.
          </p>
        )}
      </div>
      <div className="flex justify-center gap-3">
        {secondary && (
          <button
            onClick={secondary.onClick}
            className="px-6 py-2.5 rounded-xl font-medium text-sm transition-colors"
            style={{ border: '1px solid var(--border)', color: 'var(--text-muted)' }}
          >
            {secondary.label}
          </button>
        )}
        <button
          onClick={primary.onClick}
          className="px-7 py-2.5 rounded-xl font-medium text-sm"
          style={{ backgroundColor: 'var(--accent)', color: 'var(--bg)' }}
        >
          {primary.label}
        </button>
      </div>
    </div>
  )
}
