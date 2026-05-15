import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ConceptsListing from '../components/ConceptsListing'

const mockConcepts = [
  {
    id: 'c1',
    course_id: 'course1',
    name: 'Vektoren',
    type: 'definition',
    summary: 'Grundkonzept',
    target_bloom: 2,
    importance: 1.0,
    prerequisites: null,
    source_pages: [1],
  },
  {
    id: 'c2',
    course_id: 'course1',
    name: 'Matrizen',
    type: 'definition',
    summary: 'Sammlungen von Vektoren',
    target_bloom: 3,
    importance: 0.9,
    prerequisites: ['c1'],
    source_pages: [2],
  },
  {
    id: 'c3',
    course_id: 'course1',
    name: 'Eigenvektoren',
    type: 'theorem',
    summary: 'Spezielle Vektoren',
    target_bloom: 4,
    importance: 0.8,
    prerequisites: ['c2'],
    source_pages: [3],
  },
]

describe('ConceptsListing', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = vi.fn()
  })

  it('renders loading state initially', () => {
    global.fetch = vi.fn(
      () =>
        new Promise(resolve =>
          setTimeout(() =>
            resolve(
              new Response(JSON.stringify(mockConcepts), {
                status: 200,
              })
            ),
            100
          )
        )
    )

    render(<ConceptsListing courseId="course1" />)
    expect(screen.queryByText(/Lade Konzepte/i)).toBeTruthy()
  })

  it('renders concepts hierarchically after loading', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve(
        new Response(JSON.stringify(mockConcepts), {
          status: 200,
        })
      )
    )

    render(<ConceptsListing courseId="course1" />)

    await waitFor(() => {
      expect(screen.getByText('Vektoren')).toBeTruthy()
      expect(screen.getByText('Matrizen')).toBeTruthy()
      expect(screen.getByText('Eigenvektoren')).toBeTruthy()
    })
  })

  it('shows concepts in correct hierarchy order', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve(
        new Response(JSON.stringify(mockConcepts), {
          status: 200,
        })
      )
    )

    const { container } = render(<ConceptsListing courseId="course1" />)

    await waitFor(() => {
      const concepts = container.querySelectorAll('[data-concept]')
      expect(concepts.length).toBe(3)
      expect(concepts[0].textContent).toContain('Vektoren')
      expect(concepts[1].textContent).toContain('Matrizen')
      expect(concepts[2].textContent).toContain('Eigenvektoren')
    })
  })

  it('shows indentation for dependent concepts', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve(
        new Response(JSON.stringify(mockConcepts), {
          status: 200,
        })
      )
    )

    const { container } = render(<ConceptsListing courseId="course1" />)

    await waitFor(() => {
      const matrizen = container.querySelector('[data-concept-id="c2"]')
      const eigenvektoren = container.querySelector('[data-concept-id="c3"]')

      expect(matrizen?.querySelector('[data-level]')?.getAttribute('data-level')).toBe('1')
      expect(eigenvektoren?.querySelector('[data-level]')?.getAttribute('data-level')).toBe('2')
    })
  })

  it('renders refresh button and refetches on click', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve(
        new Response(JSON.stringify(mockConcepts), {
          status: 200,
        })
      )
    )

    render(<ConceptsListing courseId="course1" />)

    await waitFor(() => {
      const btn = screen.queryByRole('button', { name: /Aktualisieren/i })
      expect(btn).toBeTruthy()
    })

    const button = screen.getByRole('button', { name: /Aktualisieren/i })
    fireEvent.click(button)

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(2)
    })
  })

  it('shows empty state when no concepts', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve(
        new Response(JSON.stringify([]), {
          status: 200,
        })
      )
    )

    render(<ConceptsListing courseId="course1" />)

    await waitFor(() => {
      expect(screen.queryByText(/Keine Konzepte gefunden/i)).toBeTruthy()
    })
  })

  it('shows error state on fetch failure', async () => {
    global.fetch = vi.fn(() =>
      Promise.reject(new Error('Network error'))
    )

    render(<ConceptsListing courseId="course1" />)

    await waitFor(() => {
      expect(screen.queryByText(/Network error/i)).toBeTruthy()
    })
  })

  it('fetches correct course concepts', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve(
        new Response(JSON.stringify(mockConcepts), {
          status: 200,
        })
      )
    )

    render(<ConceptsListing courseId="my-course-123" />)

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('/api/courses/my-course-123/concepts')
    })
  })
})
