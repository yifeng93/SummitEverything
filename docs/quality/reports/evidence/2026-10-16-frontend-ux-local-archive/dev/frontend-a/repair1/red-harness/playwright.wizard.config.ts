import { resolve } from 'node:path'
import { createRequire } from 'node:module'
const require = createRequire(resolve(process.cwd(), 'package.json'))
const { defineConfig, devices } = require('@playwright/test')
const qaRoot = resolve(process.cwd(), '..', '.local/dev/frontend-a/repair1/red-harness')
export default defineConfig({
  testDir: qaRoot,
  testMatch: 'wizard-viewport.spec.cjs',
  workers: 1,
  reporter: 'list',
  outputDir: resolve(qaRoot, 'playwright-wizard-results'),
  use: { ...devices['Desktop Chrome'], headless: true, baseURL: 'http://127.0.0.1:5176' },
  webServer: { cwd: process.cwd(), command: 'npm run dev -- --host 127.0.0.1 --port 5176', url: 'http://127.0.0.1:5176', reuseExistingServer: false, timeout: 30_000 },
})
