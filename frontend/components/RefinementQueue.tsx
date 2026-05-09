'use client'

import { useCallback, useEffect, useState } from 'react'
import { MarkdownMath } from '@/components/MarkdownMath'

interface ProposedCard {
  index: number
  question: string
  answer: string
  rationale: string
  card_status: 'pending' | 'approved' | 'rejected'
}

interface Proposal {
  id: string
  concept_id: string
  concept_name: string | null
  course_name: string | null
  status: string
  cards: ProposedCard[]
  again_count: number | null
  created_at: string
}

interface EditState {
  question: string
  answer: string
}

export function RefinementQueue() {
  const [proposals, setProposals] = useState<Proposal[]>([])
  const [loading, setLoading] = useState(true)
  const [editMap, setEditMap] = useState<Record<string, EditState>>({})

  useEffect(() => {
    fetch('/api/refinements?status=pending')
      .then((r) => r.json())
      .then((data: Proposal[]) => setProposals(data))
      .catch(() => setProposals([]))
      .finally(() => setLoading(false))
  }, [])

  const editKey = (proposalId: string, cardIndex: number) => `${proposalId}:${cardIndex}`

  const startEdit = useCallback((proposalId: string, card: ProposedCard) => {
    setEditMap((prev) => ({
      ...prev,
      [editKey(proposalId, card.index)]: { question: card.question, answer: card.answer },
    }))
  }, [])

  const cancelEdit = useCallback((proposalId: string, cardIndex: number) => {
    setEditMap((prev) => {
      const next = { ...prev }
      delete next[editKey(proposalId, cardIndex)]
      return next
    })
  }, [])

  const approve = useCallback(async (proposalId: string, cardIndex: number) => {
    const key = editKey(proposalId, cardIndex)
    const override = editMap[key]
    const body = override ?? {}
    const res = await fetch(`/api/refinements/${proposalId}/cards/${cardIndex}/approve`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) return
    const data = await res.json() as { proposal: Proposal }
    setProposals((prev) =>
      data.proposal.status === 'completed'
        ? prev.filter((p) => p.id !== proposalId)
        : prev.map((p) => (p.id === proposalId ? data.proposal : p))
    )
    cancelEdit(proposalId, cardIndex)
  }, [editMap, cancelEdit])

  const reject = useCallback(async (proposalId: string, cardIndex: number) => {
    const res = await fetch(`/api/refinements/${proposalId}/cards/${cardIndex}/reject`, {
      method: 'PATCH',
    })
    if (!res.ok) return
    const data = await res.json() as { proposal: Proposal }
    setProposals((prev) =>
      data.proposal.status === 'completed'
        ? prev.filter((p) => p.id !== proposalId)
        : prev.map((p) => (p.id === proposalId ? data.proposal : p))
    )
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16 text-gray-400">
        Lade Refinements…
      </div>
    )
  }

  if (proposals.length === 0) {
    return (
      <div className="flex items-center justify-center py-16 text-gray-400">
        Keine offenen Refinements
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-8">
      {proposals.map((proposal) => (
        <div key={proposal.id} className="border border-gray-200 rounded-xl overflow-hidden">
          <div className="bg-gray-50 px-5 py-3 flex items-center justify-between border-b border-gray-200">
            <div>
              <span className="font-semibold text-gray-800">{proposal.concept_name ?? 'Konzept'}</span>
              {proposal.course_name && (
                <span className="ml-2 text-sm text-gray-500">({proposal.course_name})</span>
              )}
            </div>
            {proposal.again_count !== null && (
              <span className="text-sm text-orange-600 font-medium">
                {proposal.again_count}× &quot;Again&quot; / 14d
              </span>
            )}
          </div>

          <div className="flex flex-col divide-y divide-gray-100">
            {proposal.cards.map((card) => {
              const key = editKey(proposal.id, card.index)
              const isEditing = !!editMap[key]
              const decided = card.card_status !== 'pending'

              return (
                <div
                  key={card.index}
                  className={`px-5 py-4 flex flex-col gap-3 ${decided ? 'opacity-60' : ''}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                      Vorschlag {card.index + 1}
                    </span>
                    {card.card_status !== 'pending' && (
                      <span
                        className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                          card.card_status === 'approved'
                            ? 'bg-green-100 text-green-700'
                            : 'bg-red-100 text-red-600'
                        }`}
                      >
                        {card.card_status === 'approved' ? '✓ angenommen' : '✗ abgelehnt'}
                      </span>
                    )}
                  </div>

                  {isEditing ? (
                    <div className="flex flex-col gap-2">
                      <label className="text-xs text-gray-500">Frage:</label>
                      <textarea
                        value={editMap[key]?.question ?? ''}
                        onChange={(e) =>
                          setEditMap((prev) => ({
                            ...prev,
                            [key]: { ...prev[key]!, question: e.target.value },
                          }))
                        }
                        rows={3}
                        className="w-full font-mono text-sm border border-gray-300 rounded p-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
                        data-testid={`edit-question-${card.index}`}
                      />
                      <label className="text-xs text-gray-500">Antwort:</label>
                      <textarea
                        value={editMap[key]?.answer ?? ''}
                        onChange={(e) =>
                          setEditMap((prev) => ({
                            ...prev,
                            [key]: { ...prev[key]!, answer: e.target.value },
                          }))
                        }
                        rows={4}
                        className="w-full font-mono text-sm border border-gray-300 rounded p-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
                        data-testid={`edit-answer-${card.index}`}
                      />
                    </div>
                  ) : (
                    <div className="flex flex-col gap-1">
                      <p className="text-sm text-gray-700">
                        <span className="font-medium">F:</span> {card.question}
                      </p>
                      <p className="text-sm text-gray-600">
                        <span className="font-medium">A:</span>{' '}
                        <MarkdownMath>{card.answer}</MarkdownMath>
                      </p>
                      {card.rationale && (
                        <p className="text-xs text-gray-400 italic">Grund: {card.rationale}</p>
                      )}
                    </div>
                  )}

                  {!decided && (
                    <div className="flex gap-2">
                      <button
                        onClick={() => approve(proposal.id, card.index)}
                        className="px-3 py-1.5 bg-green-600 text-white rounded text-sm font-medium hover:bg-green-700"
                      >
                        ✓ Annehmen
                      </button>
                      {isEditing ? (
                        <button
                          onClick={() => cancelEdit(proposal.id, card.index)}
                          className="px-3 py-1.5 border border-gray-300 text-gray-600 rounded text-sm font-medium hover:bg-gray-50"
                        >
                          Abbrechen
                        </button>
                      ) : (
                        <button
                          onClick={() => startEdit(proposal.id, card)}
                          className="px-3 py-1.5 border border-gray-300 text-gray-600 rounded text-sm font-medium hover:bg-gray-50"
                        >
                          ✎ Bearbeiten
                        </button>
                      )}
                      <button
                        onClick={() => reject(proposal.id, card.index)}
                        className="px-3 py-1.5 bg-red-50 text-red-600 border border-red-200 rounded text-sm font-medium hover:bg-red-100"
                      >
                        ✗ Ablehnen
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
