import { RefinementQueue } from '@/components/RefinementQueue'

export default function RefinementPage() {
  return (
    <div className="min-w-[640px] min-h-screen flex flex-col">
      <header className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
        <span className="text-gray-700 font-medium">Refinement Queue</span>
        <a href="/review" className="text-sm text-gray-500 hover:text-gray-700">
          ← Zurück zur Review
        </a>
      </header>
      <main className="flex-1 px-6 py-6 max-w-3xl w-full mx-auto">
        <RefinementQueue />
      </main>
    </div>
  )
}
