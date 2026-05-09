import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Math } from '@/components/Math'
import HomePage from '@/app/page'

describe('HomePage', () => {
  it('renders title and subtitle', () => {
    const { container } = render(<HomePage />)
    expect(screen.getByText('StudyAssistant')).toBeTruthy()
    expect(screen.getByText('Phase 0 — Skeleton')).toBeTruthy()
  })

  it('renders Math component with katex', () => {
    const { container } = render(<Math tex="e^{i\\pi} + 1 = 0" />)
    const katexElement = container.querySelector('.katex')
    expect(katexElement).toBeTruthy()
  })
})
