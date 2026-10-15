import { randomUUID } from 'node:crypto'
import { resolve } from 'node:path'
import { defineConfig, devices } from '@playwright/test'

const evidenceRoot = resolve(process.cwd(), process.env.SUMMIT_E2E_EVIDENCE_DIR ?? '../.local/dev/frontend-c/fastapi-integration')
const runId = `${process.pid}-${randomUUID()}`
const sessionToken = `frontend-c-${runId}`

export default defineConfig({
  testDir: './e2e',
  testMatch: ['frontend-c-flow.spec.ts'],
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  outputDir: resolve(evidenceRoot, `playwright-output-${runId}`),
  use: {
    ...devices['Desktop Chrome'],
    headless: true,
    baseURL: 'http://127.0.0.1:5188',
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: 'uv --directory .. run uvicorn web.e2e.fixtures.fastapi_conflict_app:create_app --factory --host 127.0.0.1 --port 8797',
      cwd: process.cwd(),
      url: 'http://127.0.0.1:8797/api/v1/health',
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        SUMMIT_PROFILE_ROOT: resolve(evidenceRoot, `profile-${runId}`),
        SUMMIT_FIRST_USE_DEFAULTS: resolve(process.cwd(), 'e2e/fixtures/empty-first-use-defaults.json'),
        SUMMIT_SESSION_TOKEN: sessionToken,
        SUMMIT_API_PORT: '8797',
        SUMMIT_WEB_PORT: '5188',
        SUMMIT_OFFLINE_GUARD_ACTIVE: '1',
      },
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5188',
      cwd: process.cwd(),
      url: 'http://127.0.0.1:5188',
      reuseExistingServer: false,
      timeout: 60_000,
      env: { SUMMIT_API_TARGET: 'http://127.0.0.1:8797', SUMMIT_SESSION_TOKEN: sessionToken },
    },
  ],
})
