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

export default function ConceptsListing({ courseId }: { courseId: string }) {
  const [concepts, setConcepts] = useState<Concept[]>([])
  const [hierarchy, setHierarchy] = useState<ConceptNode[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const buildHierarchy = (concepts: Concept[]): ConceptNode[] => {
    const conceptMap = new Map(concepts.map(c => [c.id, c]))
    const roots: ConceptNode[] = []
    const processed = new Set<string>()

    // Rekursiv Kinder für jeden Concept finden
    const buildNode = (concept: Concept, level: number): ConceptNode => {
      const children: ConceptNode[] = []

      // Finde alle Konzepte, die diesen Concept als Prerequisite haben
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

      return {
        concept,
        level,
        children,
      }
    }

    // Starte mit Konzepten ohne Prerequisites
    for (const concept of concepts) {
      if (!concept.prerequisites || concept.prerequisites.length === 0) {
        processed.add(concept.id)
        roots.push(buildNode(concept, 0))
      }
    }

    // Verarbeite remaining concepts (mit ungültigen Prerequisites)
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
    const indentClass = `ml-${node.level * 4}`
    const paddingLeft = node.level * 16

    return (
      <div key={node.concept.id} data-concept data-concept-id={node.concept.id}>
        <div
          className="px-4 py-3 border-l-2 border-transparent hover:border-blue-400 hover:bg-slate-50 transition-colors"
          style={{ paddingLeft: `${paddingLeft}px` }}
          data-level={node.level}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="font-medium text-sm" style={{ color: 'var(--text)' }}>
                  {node.concept.name}
                </h3>
                <span
                  className="text-xs px-2 py-0.5 rounded-full"
                  style={{
                    backgroundColor: 'var(--bg-secondary)',
                    color: 'var(--text-muted)',
                  }}
                >
                  {node.concept.type}
                </span>
              </div>

              {node.concept.summary && (
                <p
                  className="text-xs line-clamp-2"
                  style={{ color: 'var(--text-muted)' }}
                >
                  {node.concept.summary}
                </p>
              )}

              <div className="flex items-center gap-3 mt-2 text-xs">
                {node.concept.importance && (
                  <span style={{ color: 'var(--text-muted)' }}>
                    Wichtigkeit: {(node.concept.importance * 100).toFixed(0)}%
                  </span>
                )}
                {node.concept.source_pages && node.concept.source_pages.length > 0 && (
                  <span style={{ color: 'var(--text-muted)' }}>
                    Seite: {node.concept.source_pages.join(', ')}
                  </span>
                )}
              </div>
            </div>

            {node.concept.target_bloom && (
              <div
                className="text-xs px-2 py-1 rounded"
                style={{
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-muted)',
                }}
                title="Bloom-Level (1-6)"
              >
                L{node.concept.target_bloom}
              </div>
            )}
          </div>
        </div>

        {node.children.length > 0 && (
          <div>
            {node.children.map(child => renderNode(child))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="min-h-[calc(100vh-3.5rem)] py-12">
      <div className="max-w-4xl mx-auto px-6">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-2xl font-semibold" style={{ color: 'var(--text)' }}>
            Konzepte
          </h1>
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

        {loading && concepts.length === 0 && (
          <div className="text-center py-12">
            <p style={{ color: 'var(--text-muted)' }}>Lade Konzepte...</p>
          </div>
        )}

        {error && (
          <div
            className="p-4 rounded-lg border-l-4"
            style={{
              borderColor: '#ef4444',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
            }}
          >
            <p style={{ color: '#ef4444' }}>{error}</p>
          </div>
        )}

        {!loading && concepts.length === 0 && !error && (
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
        )}

        {!loading && concepts.length > 0 && (
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
