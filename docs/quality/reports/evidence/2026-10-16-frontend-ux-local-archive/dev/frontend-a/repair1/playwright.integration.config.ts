import { resolve } from 'node:path'
import { randomUUID } from 'node:crypto'
import { createRequire } from 'node:module'
const require = createRequire(resolve(process.cwd(), 'package.json'))
const { defineConfig, devices } = require('@playwright/test')

const repoRoot = resolve(process.cwd(), '..')
const qaRoot = resolve(repoRoot, '.local/dev/frontend-a/repair1')
const sessionToken = `playwright-qa-${process.pid}-${randomUUID()}`

export default defineConfig({
  testDir: resolve(qaRoot, 'integration-harness'),
  testMatch: 'first-use-real.spec.ts',
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  outputDir: resolve(qaRoot, `integration-results-${process.pid}`),
  use: {
    ...devices['Desktop Chrome'],
    headless: true,
    baseURL: 'http://127.0.0.1:5174',
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: 'uv --directory .. run uvicorn summit_everything.api.app:app --host 127.0.0.1 --port 8794',
      cwd: process.cwd(),
      url: 'http://127.0.0.1:8794/api/v1/health',
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        SUMMIT_PROFILE_ROOT: resolve(qaRoot, `profile-repair1-${process.pid}`),
        SUMMIT_FIRST_USE_DEFAULTS: resolve(process.cwd(), 'e2e/fixtures/empty-first-use-defaults.json'),
        SUMMIT_SESSION_TOKEN: sessionToken,
        SUMMIT_API_PORT: '8794',
        SUMMIT_WEB_PORT: '5174',
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
