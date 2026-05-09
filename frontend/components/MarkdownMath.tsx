'use client'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'

interface Props {
  children: string
}

export function MarkdownMath({ children }: Props) {
  return (
    <div className="prose prose-sm max-w-none overflow-x-auto">
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeKatex]}
      >
        {children}
      </ReactMarkdown>
    </div>
  )
}
