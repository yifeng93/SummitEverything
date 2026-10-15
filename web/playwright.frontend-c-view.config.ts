import { randomUUID } from 'node:crypto'
import { resolve } from 'node:path'
import { defineConfig, devices } from '@playwright/test'

const repoRoot = resolve(process.cwd(), '..')
const runId = `${process.pid}-${randomUUID()}`
const evidenceRoot = resolve(repoRoot, `.local/dev/frontend-c/view-${runId}`)

export default defineConfig({
  testDir: './e2e',
  testMatch: ['frontend-c-view.spec.ts'],
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  outputDir: resolve(evidenceRoot, 'playwright-output'),
  use: { ...devices['Desktop Chrome'], headless: true, baseURL: 'http://127.0.0.1:5191' },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 5191',
    cwd: process.cwd(),
    url: 'http://127.0.0.1:5191',
    reuseExistingServer: false,
    timeout: 30_000,
  },
})
