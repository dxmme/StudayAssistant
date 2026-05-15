'use client'

import Link from 'next/link'
import React from 'react'
import ConceptsListing from '@/components/ConceptsListing'

interface ConceptsPageProps {
  params: Promise<{ courseId: string }>
}

export default function ConceptsPage({ params }: ConceptsPageProps) {
  const { courseId } = React.use(params)
  return (
    <>
      <div className="sticky top-0 z-10 bg-white border-b px-6 py-3" style={{ borderColor: 'var(--border)' }}>
        <div className="max-w-4xl mx-auto">
          <Link
            href={`/courses/${courseId}`}
            className="inline-flex items-center gap-1.5 text-sm transition-colors"
            style={{ color: 'var(--text-muted)' }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5M12 5l-7 7 7 7" />
            </svg>
            Zurück zum Kurs
          </Link>
        </div>
      </div>
      <ConceptsListing courseId={courseId} />
    </>
  )
}
