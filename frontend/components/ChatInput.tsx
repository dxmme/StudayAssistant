'use client'
import { useRef, useState, KeyboardEvent } from 'react'

interface Props {
  onSend: (message: string) => void
  disabled: boolean
}

export function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState('')
  const ref = useRef<HTMLTextAreaElement>(null)

  function handleKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  function submit() {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue('')
  }

  return (
    <div className="flex items-end gap-2">
      <textarea
        ref={ref}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKey}
        disabled={disabled}
        rows={2}
        placeholder={disabled ? 'Coach denkt nach …' : 'Schreibe deine Antwort … (Enter zum Senden, Shift+Enter für Zeilenumbruch)'}
        className="flex-1 resize-none rounded-lg border border-gray-300 px-3 py-2 text-base focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
        aria-label="Antwort"
      />
      <button
        onClick={submit}
        disabled={disabled || !value.trim()}
        className="px-4 py-2 bg-blue-600 text-white rounded-lg disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-blue-700 transition-colors"
      >
        Senden
      </button>
    </div>
  )
}
