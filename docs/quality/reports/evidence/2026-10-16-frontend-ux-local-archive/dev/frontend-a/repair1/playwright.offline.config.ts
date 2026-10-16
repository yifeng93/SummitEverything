import { resolve } from 'node:path'
import { createRequire } from 'node:module'
const require = createRequire(resolve(process.cwd(), 'package.json'))
const { defineConfig, devices } = require('@playwright/test')

const qaRoot = resolve(process.cwd(), '..', '.local/dev/frontend-a/repair1')

export default defineConfig({
  testDir: resolve(process.cwd(), 'e2e'),
  testMatch: ['viewport.spec.ts', 'first-use.spec.ts'],
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  outputDir: resolve(qaRoot, 'playwright-mock-results'),
  use: {
    ...devices['Desktop Chrome'],
    headless: true,
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
  },
  webServer: {
    cwd: process.cwd(),
    command: 'npm run dev -- --host 127.0.0.1',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: false,
    timeout: 30_000,
  },
})
