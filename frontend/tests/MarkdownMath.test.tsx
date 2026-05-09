import { render } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { MarkdownMath } from '@/components/MarkdownMath'

describe('MarkdownMath', () => {
  it('renders inline math $x^2$ as KaTeX span', async () => {
    const { container } = render(<MarkdownMath>{'$x^2$'}</MarkdownMath>)
    // wait for any async rendering
    await new Promise((r) => setTimeout(r, 0))
    const katexEl = container.querySelector('.katex')
    expect(katexEl).toBeTruthy()
  })

  it('renders display math $$...$$ as KaTeX display element', async () => {
    const { container } = render(
      // remark-math requires $$ on its own line for block (display) math
      <MarkdownMath>{'$$\n\\sum_i x_i\n$$'}</MarkdownMath>
    )
    await new Promise((r) => setTimeout(r, 0))
    const katexEl = container.querySelector('.katex-display')
    expect(katexEl).toBeTruthy()
  })

  it('renders plain text without katex wrapper', () => {
    const { container } = render(<MarkdownMath>{'Hello world'}</MarkdownMath>)
    expect(container.textContent).toContain('Hello world')
    expect(container.querySelector('.katex')).toBeNull()
  })
})
