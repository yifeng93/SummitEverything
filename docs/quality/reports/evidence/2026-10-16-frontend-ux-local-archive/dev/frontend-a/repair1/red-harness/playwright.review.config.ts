import { resolve } from 'node:path'
import { createRequire } from 'node:module'
const require = createRequire(resolve(process.cwd(), 'package.json'))
const { defineConfig, devices } = require('@playwright/test')
const qaRoot = resolve(process.cwd(), '..', '.local/dev/frontend-a/repair1/red-harness')
export default defineConfig({
  testDir: qaRoot,
  testMatch: 'settings-review.spec.cjs',
  workers: 1,
  reporter: 'list',
  outputDir: resolve(qaRoot, 'playwright-review-results'),
  use: { ...devices['Desktop Chrome'], headless: true, baseURL: 'http://127.0.0.1:5175' },
  webServer: { cwd: process.cwd(), command: 'npm run dev -- --host 127.0.0.1 --port 5175', url: 'http://127.0.0.1:5175', reuseExistingServer: false, timeout: 30_000 },
})
