'use client'

import { useEffect, useState } from 'react'

interface Concept {
  id: string
  course_id: string
  name: string
  type: string
  summary: string | null
  target_bloom: number | null
  importance: number
  prerequisites: string[] | null
  source_pages: number[] | null
}

interface ConceptNode {
  concept: Concept
  level: number
  children: ConceptNode[]
}

const BLOOM_LABELS: Record<number, string> = {
  1: 'Remember',
  2: 'Understand',
  3: 'Apply',
  4: 'Analyze',
  5: 'Evaluate',
  6: 'Create',
}

const formatPercentage = (value: number): string => String(Math.floor(value * 100))

const TYPE_COLORS = {
  definition: { bg: '#dbeafe', text: '#0369a1' },
  theorem: { bg: '#fce7f3', text: '#be185d' },
  proof: { bg: '#f3e8ff', text: '#7e22ce' },
  example: { bg: '#fef3c7', text: '#b45309' },
  default: { bg: '#f3f4f6', text: '#6b7280' },
} as const

export default function ConceptsListing({ courseId }: { courseId: string }) {
  const [concepts, setConcepts] = useState<Concept[]>([])
  const [hierarchy, setHierarchy] = useState<ConceptNode[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const buildHierarchy = (concepts: Concept[]): ConceptNode[] => {
    const conceptMap = new Map(concepts.map(c => [c.id, c]))
    const roots: ConceptNode[] = []
    const processed = new Set<string>()

    const buildNode = (concept: Concept, level: number): ConceptNode => {
      const children: ConceptNode[] = []
      for (const c of concepts) {
        if (
          !processed.has(c.id) &&
          c.prerequisites &&
          c.prerequisites.includes(concept.id)
        ) {
          processed.add(c.id)
          children.push(buildNode(c, level + 1))
        }
      }
      return { concept, level, children }
    }

    for (const concept of concepts) {
      if (!concept.prerequisites || concept.prerequisites.length === 0) {
        processed.add(concept.id)
        roots.push(buildNode(concept, 0))
      }
    }

    for (const concept of concepts) {
      if (!processed.has(concept.id)) {
        processed.add(concept.id)
        roots.push(buildNode(concept, 0))
      }
    }

    return roots
  }

  const fetchConcepts = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await fetch(`/api/courses/${courseId}/concepts`)

      if (!response.ok) {
        throw new Error('Fehler beim Laden der Konzepte')
      }

      const data: Concept[] = await response.json()
      setConcepts(data)
      setHierarchy(buildHierarchy(data))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchConcepts()
  }, [courseId])

  const renderNode = (node: ConceptNode) => {
    const typeColor = TYPE_COLORS[node.concept.type as keyof typeof TYPE_COLORS] || TYPE_COLORS.default
    const marginLeft = node.level * 24

    return (
      <div key={node.concept.id} data-concept data-concept-id={node.concept.id}>
        <div
          className="group px-5 py-4 border-l-2 border-gray-200 hover:border-blue-400 hover:bg-blue-50 transition-all duration-150"
          style={{ marginLeft: `${marginLeft}px` }}
          data-level={node.level}
        >
          {/* Header: Name + Badge */}
          <div className="flex items-start justify-between gap-3 mb-2">
            <div className="flex-1 min-w-0">
              <h3
                className="text-sm font-semibold leading-tight mb-1"
                style={{ color: 'var(--text)' }}
              >
                {node.concept.name}
              </h3>
              <div className="flex items-center gap-2 flex-wrap">
                <span
                  className="text-xs font-medium px-2.5 py-1 rounded-md"
                  style={{
                    backgroundColor: typeColor.bg,
                    color: typeColor.text,
                  }}
                >
                  {node.concept.type}
                </span>
                {node.concept.target_bloom && (
                  <span
                    className="text-xs font-medium px-2.5 py-1 rounded-md"
                    title="Bloom's Taxonomy Level"
                    style={{
                      backgroundColor: 'var(--bg-secondary)',
                      color: 'var(--text-muted)',
                    }}
                  >
                    {BLOOM_LABELS[node.concept.target_bloom]}
                  </span>
                )}
              </div>
            </div>

            {/* Importance badge */}
            {node.concept.importance && node.concept.importance < 1 && (
              <div
                className="text-xs font-semibold px-2.5 py-1 rounded-md whitespace-nowrap"
                style={{
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-muted)',
                }}
              >
                {formatPercentage(node.concept.importance)}%
              </div>
            )}
          </div>

          {/* Summary */}
          {node.concept.summary && (
            <p className="mt-3 mb-3 text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
              {node.concept.summary}
            </p>
          )}

          {/* Footer: Metadata */}
          <div className="flex items-center gap-3 mt-3 text-xs">
            {node.concept.source_pages && node.concept.source_pages.length > 0 && (
              <span
                style={{ color: 'var(--text-muted)' }}
                className="flex items-center gap-1"
              >
                <span>📄</span>
                <span>S. {node.concept.source_pages.join(', ')}</span>
              </span>
            )}
            {node.level > 0 && (
              <span style={{ color: 'var(--text-muted)' }} className="flex items-center gap-1">
                <span>📚</span>
                <span>Builds on {node.level} concept{node.level > 1 ? 's' : ''}</span>
              </span>
            )}
          </div>
        </div>

        {/* Render children */}
        {node.children.length > 0 && (
          <div>
            {node.children.map(child => renderNode(child))}
          </div>
        )}
      </div>
    )
  }

  if (loading && concepts.length === 0) {
    return (
      <div className="min-h-[calc(100vh-3.5rem)] py-12">
        <div className="max-w-4xl mx-auto px-6">
          <div className="text-center py-12">
            <p style={{ color: 'var(--text-muted)' }}>Lade Konzepte...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-[calc(100vh-3.5rem)] py-12">
        <div className="max-w-4xl mx-auto px-6">
          <div
            className="p-4 rounded-lg border-l-4"
            style={{
              borderColor: '#ef4444',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
            }}
          >
            <p style={{ color: '#ef4444' }}>{error}</p>
          </div>
        </div>
      </div>
    )
  }

  if (!loading && concepts.length === 0) {
    return (
      <div className="min-h-[calc(100vh-3.5rem)] py-12">
        <div className="max-w-4xl mx-auto px-6">
          <div className="text-center py-12">
            <p style={{ color: 'var(--text-muted)' }} className="mb-6">
              Keine Konzepte gefunden.
            </p>
            <p
              style={{ color: 'var(--text-muted)' }}
              className="text-sm mb-6"
            >
              Laden Sie Materialien hoch und verarbeiten Sie diese, um Konzepte zu generieren.
            </p>
            <button
              onClick={fetchConcepts}
              className="px-4 py-2 rounded-lg font-medium text-sm transition-colors"
              style={{
                backgroundColor: 'var(--accent)',
                color: 'white',
              }}
            >
              Erneut versuchen
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-[calc(100vh-3.5rem)] py-12">
      <div className="max-w-4xl mx-auto px-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2" style={{ color: 'var(--text)' }}>
              Konzepte
            </h1>
            <p style={{ color: 'var(--text-muted)' }} className="text-sm">
              {concepts.length} Konzept{concepts.length !== 1 ? 'e' : ''} · Hierarchisch sortiert nach Abhängigkeiten
            </p>
          </div>
          <button
            onClick={fetchConcepts}
            disabled={loading}
            className="px-4 py-2 rounded-lg font-medium text-sm transition-colors"
            style={{
              backgroundColor: loading ? 'var(--bg-secondary)' : 'var(--accent)',
              color: loading ? 'var(--text-muted)' : 'white',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.6 : 1,
            }}
          >
            {loading ? 'Lädt...' : 'Aktualisieren'}
          </button>
        </div>

        {/* Concepts list */}
        {concepts.length > 0 && (
          <div
            className="border rounded-lg overflow-hidden"
            style={{
              borderColor: 'var(--border)',
              backgroundColor: 'var(--bg)',
            }}
          >
            {hierarchy.map(node => renderNode(node))}
          </div>
        )}
      </div>
    </div>
  )
}
