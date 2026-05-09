import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests-e2e',
  fullyParallel: false,
  retries: 0,
  use: {
    baseURL: 'http://localhost:3000',
    headless: true,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  // Start backend + frontend before running E2E tests
  webServer: [
    {
      command: 'cd ../backend && uv run uvicorn app.main:app --port 8000',
      url: 'http://localhost:8000/health',
      reuseExistingServer: true,
      timeout: 30_000,
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:3000',
      reuseExistingServer: true,
      timeout: 30_000,
    },
  ],
})
