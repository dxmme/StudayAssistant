import { Math } from '@/components/Math'
import Link from 'next/link'

export default function HomePage() {
  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-3.5rem)]">
      <div className="text-center max-w-xl px-6">
        <h1
          className="text-3xl font-semibold mb-3 tracking-tight"
          style={{ color: 'var(--text)' }}
        >
          StudyAssistant
        </h1>
        <p className="text-sm mb-10" style={{ color: 'var(--text-muted)' }}>
          ML-Master Tübingen · Active Recall · Spaced Repetition
        </p>

        <div
          className="rounded-xl px-8 py-6 mb-10"
          style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)' }}
        >
          <Math tex="e^{i\pi} + 1 = 0" />
        </div>

        <div className="flex gap-3 justify-center">
          <Link
            href="/courses"
            className="px-5 py-2 rounded-lg text-sm font-medium transition-all"
            style={{ backgroundColor: 'var(--accent)', color: '#000' }}
          >
            Kurse öffnen
          </Link>
          <Link
            href="/plan"
            className="px-5 py-2 rounded-lg text-sm font-medium transition-all"
            style={{ backgroundColor: 'var(--surface-2)', color: 'var(--text)', border: '1px solid var(--border)' }}
          >
            Tagesplan
          </Link>
        </div>
      </div>
    </div>
  )
}
