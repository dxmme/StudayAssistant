'use client'

import { useEffect, useState } from 'react'
import { MarkdownMath } from '@/components/MarkdownMath'

interface Props {
  cardId: string
  onClose: () => void
}

export function WorkedExampleModal({ cardId, onClose }: Props) {
  const [loading, setLoading] = useState(true)
  const [content, setContent] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`/api/cards/${cardId}/worked-example`, { method: 'POST' })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json() as Promise<{ content: string }>
      })
      .then((data) => setContent(data.content))
      .catch(() => setError('Lösung konnte nicht geladen werden.'))
      .finally(() => setLoading(false))
  }, [cardId])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
      role="dialog"
      aria-modal="true"
      aria-label="Worked Example"
    >
      <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-800">Worked Example</h2>
          <button
            onClick={onClose}
            aria-label="Schließen"
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
          >
            ×
          </button>
        </div>

        {loading && (
          <div className="flex items-center gap-2 text-gray-500 py-8 justify-center">
            <div
              role="status"
              aria-label="Lädt..."
              className="w-5 h-5 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin"
            />
            <span>Lösung wird generiert…</span>
          </div>
        )}

        {!loading && error && (
          <p className="text-red-600 text-sm py-4">{error}</p>
        )}

        {!loading && content && (
          <MarkdownMath>{content}</MarkdownMath>
        )}
      </div>
    </div>
  )
}
