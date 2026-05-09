import { MarkdownMath } from './MarkdownMath'

export interface Turn {
  role: 'user' | 'assistant'
  content: string
}

interface Props {
  turn: Turn
  // When true, render as plain text (used for the actively-streaming assistant turn).
  // KaTeX rerender happens once when streaming finishes and we flip this off.
  streaming?: boolean
}

export function ChatTurn({ turn, streaming }: Props) {
  const isUser = turn.role === 'user'
  return (
    <div className={`flex flex-col gap-2 ${isUser ? 'items-end' : 'items-start'}`}>
      <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">
        {isUser ? 'Du' : 'Coach'}
      </span>
      <div
        className={`max-w-[85%] px-4 py-3 rounded-lg ${
          isUser ? 'bg-blue-50 text-gray-900' : 'bg-gray-50 text-gray-900'
        }`}
      >
        {streaming ? (
          // While streaming: plain text (KaTeX renders once on completion)
          <pre className="whitespace-pre-wrap font-sans text-base">{turn.content || '…'}</pre>
        ) : (
          <MarkdownMath>{turn.content}</MarkdownMath>
        )}
      </div>
    </div>
  )
}
