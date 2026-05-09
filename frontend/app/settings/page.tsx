import { SettingsForm } from '@/components/SettingsForm'

export default function SettingsPage() {
  return (
    <div className="min-h-screen bg-white py-12">
      <div className="max-w-lg mx-auto px-4">
        <h1 className="text-2xl font-bold mb-8">Einstellungen</h1>
        <SettingsForm />
      </div>
    </div>
  )
}
