import React from 'react'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { Node } from '@xyflow/react'
import { ConceptGraph } from '@/components/ConceptGraph'

const mockPush = vi.fn()
const mockBack = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, back: mockBack }),
}))

vi.mock('@xyflow/react', () => ({
  ReactFlow: ({
    nodes,
    onNodeClick,
  }: {
    nodes: Array<Node>
    onNodeClick?: (e: React.MouseEvent, node: Node) => void
  }) => (
    <div data-testid="react-flow">
      {nodes.map((n) => (
        <div
          key={n.id}
          data-testid={`node-${n.id}`}
          onClick={(e) => onNodeClick?.(e, n)}
        >
          {String(n.data.label)}
        </div>
      ))}
    </div>
  ),
  Background: () => null,
  Controls: () => null,
  Handle: () => null,
  Position: { Top: 'top', Bottom: 'bottom' },
}))

const MOCK_GRAPH = {
  nodes: [
    { id: 'c1', name: 'SGD', summary: 'Stochastic Gradient Descent', type: 'algorithm' },
    { id: 'c2', name: 'Gradient Descent', summary: 'Basic optimizer', type: 'algorithm' },
  ],
  edges: [{ src: 'c1', dst: 'c2', relation: 'prerequisite' }],
}

function setupFetch(data = MOCK_GRAPH) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => ({ ok: true, json: async () => data }) as Response),
  )
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: false })
  mockPush.mockClear()
  mockBack.mockClear()
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})

describe('ConceptGraph', () => {
  it('renders loading state before fetch resolves', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))
    render(<ConceptGraph courseId="course-1" />)
    expect(screen.getByText('Lade Graph…')).toBeTruthy()
  })

  it('renders node names after fetch', async () => {
    setupFetch()
    render(<ConceptGraph courseId="course-1" />)
    await act(async () => {
      await vi.runAllTimersAsync()
    })
    expect(screen.getByText('SGD')).toBeTruthy()
    expect(screen.getByText('Gradient Descent')).toBeTruthy()
  })

  it('renders empty state when no nodes returned', async () => {
    setupFetch({ nodes: [], edges: [] })
    render(<ConceptGraph courseId="course-1" />)
    await act(async () => {
      await vi.runAllTimersAsync()
    })
    expect(screen.getByText('Keine Concepts gefunden.')).toBeTruthy()
  })

  it('calls router.push with review href on node click', async () => {
    setupFetch()
    render(<ConceptGraph courseId="course-1" />)
    await act(async () => {
      await vi.runAllTimersAsync()
    })
    fireEvent.click(screen.getByTestId('node-c1'))
    expect(mockPush).toHaveBeenCalledWith('/courses/course-1/review')
  })
})
