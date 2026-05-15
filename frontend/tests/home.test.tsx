import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Math } from '@/components/Math'
import HomePage from '@/app/page'

describe('HomePage', () => {
  it('renders title and nav links', () => {
    const { container } = render(<HomePage />)
    expect(screen.getByText('StudyAssistant')).toBeTruthy()
    expect(container.querySelector('a[href="/courses"]')).toBeTruthy()
  })

  it('renders Math component with katex', () => {
    const { container } = render(<Math tex="e^{i\\pi} + 1 = 0" />)
    const katexElement = container.querySelector('.katex')
    expect(katexElement).toBeTruthy()
  })
})
