import { SettingsForm } from '@/components/SettingsForm'

export default function SettingsPage() {
  return (
    <div className="min-h-[calc(100vh-3.5rem)] py-12">
      <div className="max-w-lg mx-auto px-6">
        <h1 className="text-2xl font-semibold mb-10 tracking-tight" style={{ color: 'var(--text)' }}>
          Einstellungen
        </h1>
        <SettingsForm />
      </div>
    </div>
  )
}
