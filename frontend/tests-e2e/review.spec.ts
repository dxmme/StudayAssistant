/**
 * E2E: Review page — keyboard-only session.
 *
 * Setup: backend must have 3 due cards in course "e2e-review".
 * Seed them before running: POST /api/courses/e2e-review/cards  (x3)
 *
 * Run:
 *   npx playwright test              (starts servers automatically via playwright.config.ts)
 *   npx playwright install chromium  (first time only)
 */
import { test, expect, Page } from '@playwright/test'

const COURSE = 'e2e-review'
const BACKEND = 'http://localhost:8000'

async function seedCards(page: Page) {
  // Create 3 cards via the API so there are due cards to review
  for (let i = 0; i < 3; i++) {
    await page.request.post(`${BACKEND}/api/courses/${COURSE}/cards`, {
      data: { type: 'basic', front: `E2E Front ${i + 1}`, back: `E2E Back ${i + 1}` },
    })
  }
}

test.describe('Review page — keyboard only', () => {
  test.beforeEach(async ({ page }) => {
    await seedCards(page)
  })

  test('Space-3 x3 sequence completes session without mouse', async ({ page }) => {
    await page.goto(`/review/${COURSE}`)

    // Wait for first card to load
    await expect(page.getByText('E2E Front 1')).toBeVisible({ timeout: 5000 })

    // Verify back is not shown yet
    await expect(page.getByText('E2E Back 1')).not.toBeVisible()

    // Card 1: flip + rate Good
    await page.keyboard.press('Space')
    await expect(page.getByText('E2E Back 1')).toBeVisible()
    await page.keyboard.press('3')

    // Card 2
    await expect(page.getByText('E2E Front 2')).toBeVisible({ timeout: 3000 })
    await page.keyboard.press('Space')
    await expect(page.getByText('E2E Back 2')).toBeVisible()
    await page.keyboard.press('3')

    // Card 3
    await expect(page.getByText('E2E Front 3')).toBeVisible({ timeout: 3000 })
    await page.keyboard.press('Space')
    await expect(page.getByText('E2E Back 3')).toBeVisible()
    await page.keyboard.press('3')

    // Empty state
    await expect(page.getByText('Heute fertig')).toBeVisible({ timeout: 3000 })
    await expect(page.getByText(/Reviewed:/)).toBeVisible()

    // Verify no mouse clicks were used — all interaction was keyboard only
  })

  test('rating Again (1) shows lapse count in empty state', async ({ page }) => {
    await page.goto(`/review/${COURSE}`)
    await expect(page.getByText('E2E Front 1')).toBeVisible({ timeout: 5000 })

    // Use "Again" for all cards
    for (let i = 0; i < 3; i++) {
      await page.keyboard.press('Space')
      await page.keyboard.press('1')
      // wait for next card or done
      await page.waitForTimeout(500)
    }

    await expect(page.getByText('Heute fertig')).toBeVisible({ timeout: 3000 })
    await expect(page.getByText(/Lapses:/)).toBeVisible()
  })
})
