import { Math } from '@/components/Math'

export default function HomePage() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-white">
      <div className="text-center max-w-[720px] px-4">
        <h1 className="text-4xl font-bold mb-4">StudyAssistant</h1>
        <p className="text-xl text-gray-600 mb-12">Phase 0 — Skeleton</p>
        <div className="bg-gray-50 p-8 rounded-lg border border-gray-200">
          <Math tex="e^{i\\pi} + 1 = 0" />
        </div>
      </div>
    </div>
  )
}
