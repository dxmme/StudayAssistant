import { MarkdownMath } from './MarkdownMath'
import type { Card } from '@/types/card'

interface Props {
  card: Card
  flipped: boolean
}

export function CardView({ card, flipped }: Props) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <span className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2 block">
          Front
        </span>
        <div className="text-lg text-gray-900">
          <MarkdownMath>{card.front}</MarkdownMath>
        </div>
      </div>

      {flipped && (
        <>
          <hr className="border-gray-200" />
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2 block">
              Back
            </span>
            <div className="text-lg text-gray-900 overflow-x-auto">
              <MarkdownMath>{card.back}</MarkdownMath>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
