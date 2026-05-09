const RATINGS = [
  { key: '1', label: 'Again' },
  { key: '2', label: 'Hard' },
  { key: '3', label: 'Good' },
  { key: '4', label: 'Easy' },
] as const

interface Props {
  flipped: boolean
  disabled: boolean
}

export function RatingBar({ flipped, disabled }: Props) {
  if (!flipped) {
    return (
      <div className="flex items-center gap-2 text-gray-500 text-sm">
        <kbd className="px-2 py-1 bg-gray-100 border border-gray-300 rounded text-xs font-mono">
          Space
        </kbd>
        <span>umdrehen</span>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="flex gap-6">
        {RATINGS.map(({ key, label }) => (
          <div key={key} className="flex flex-col items-center gap-1">
            <kbd
              className={`px-3 py-1 border rounded text-sm font-mono transition-colors ${
                disabled
                  ? 'bg-gray-50 border-gray-200 text-gray-400'
                  : 'bg-gray-100 border-gray-300 text-gray-700'
              }`}
            >
              {key}
            </kbd>
            <span className="text-sm text-gray-600">{label}</span>
          </div>
        ))}
      </div>
      <p className="text-xs text-gray-400">Drücke 1–4 zur Bewertung</p>
    </div>
  )
}
