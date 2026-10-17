import { resolve } from 'node:path'
import { randomUUID } from 'node:crypto'
import { defineConfig, devices } from '@playwright/test'

const repoRoot = resolve(process.cwd(), '..')
const evidenceRoot = resolve(repoRoot, '.local/dev/2026-10-16-frontend-usability/integration')
const sessionToken = `playwright-${process.pid}-${randomUUID()}`

export default defineConfig({
  testDir: './e2e',
  testMatch: ['approval-today.spec.ts'],
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  use: {
    ...devices['Desktop Chrome'],
    headless: true,
    baseURL: 'http://127.0.0.1:5174',
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: 'uv --directory .. run uvicorn web.e2e.fixtures.fastapi_conflict_app:create_app --factory --host 127.0.0.1 --port 8794',
      cwd: process.cwd(),
      url: 'http://127.0.0.1:8794/api/v1/health',
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        SUMMIT_PROFILE_ROOT: resolve(evidenceRoot, `profile-${process.pid}`),
        SUMMIT_FIRST_USE_DEFAULTS: resolve(process.cwd(), 'e2e/fixtures/empty-first-use-defaults.json'),
        SUMMIT_SESSION_TOKEN: sessionToken,
        SUMMIT_API_PORT: '8794',
        SUMMIT_WEB_PORT: '5174',
        SUMMIT_OFFLINE_GUARD_ACTIVE: '1',
      },
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5174',
      cwd: process.cwd(),
      url: 'http://127.0.0.1:5174',
      reuseExistingServer: false,
      timeout: 60_000,
      env: { SUMMIT_API_TARGET: 'http://127.0.0.1:8794', SUMMIT_SESSION_TOKEN: sessionToken },
    },
  ],
})
