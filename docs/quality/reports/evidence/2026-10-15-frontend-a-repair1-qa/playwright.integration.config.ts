import { resolve } from 'node:path'
import { createRequire } from 'node:module'
import { randomUUID } from 'node:crypto'

const playwright = createRequire(resolve(process.cwd(), 'package.json'))('@playwright/test')
const { defineConfig, devices } = playwright

const repoRoot = resolve(process.cwd(), '..')
const qaRoot = resolve(repoRoot, '.local/qa/frontend-a-repair1')
const sessionToken = `qa-repair1-${process.pid}-${randomUUID()}`
const pythonPath = [resolve(repoRoot, 'scripts/offline_guard'), resolve(repoRoot, 'src')].join(':')

export default defineConfig({
  testDir: resolve(repoRoot, '.local/qa/frontend-a-repair1/harness'),
  testMatch: 'first-use-real.spec.ts',
  outputDir: resolve(qaRoot, 'integration-results'),
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
      command: 'uv --directory .. run uvicorn summit_everything.api.app:app --host 127.0.0.1 --port 8794',
      cwd: process.cwd(),
      url: 'http://127.0.0.1:8794/api/v1/health',
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        PYTHONPATH: pythonPath,
        UV_PROJECT_ENVIRONMENT: resolve(qaRoot, '.venv'),
        UV_OFFLINE: '1',
        SUMMIT_PROFILE_ROOT: resolve(qaRoot, `profile-${process.pid}`),
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
      timeout: 30_000,
      env: { SUMMIT_API_TARGET: 'http://127.0.0.1:8794', SUMMIT_SESSION_TOKEN: sessionToken },
    },
  ],
})
