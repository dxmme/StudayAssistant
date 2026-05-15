'use client'

import { CourseList } from '@/components/CourseList'
import { CreateCourseForm } from '@/components/CreateCourseForm'
import { useState } from 'react'

export default function CoursesPage() {
  const [refreshKey, setRefreshKey] = useState(0)

  return (
    <div className="min-h-[calc(100vh-3.5rem)] py-12">
      <div className="max-w-3xl mx-auto px-6">
        <h1
          className="text-2xl font-semibold mb-10 tracking-tight"
          style={{ color: 'var(--text)' }}
        >
          Meine Kurse
        </h1>

        <div className="grid gap-8 md:grid-cols-[1fr_320px]">
          <CourseList key={refreshKey} onDeleted={() => setRefreshKey(k => k + 1)} />
          <CreateCourseForm onSuccess={() => setRefreshKey(k => k + 1)} />
        </div>
      </div>
    </div>
  )
}
