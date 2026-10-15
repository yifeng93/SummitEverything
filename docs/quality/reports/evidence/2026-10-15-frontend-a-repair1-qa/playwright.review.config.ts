import { resolve } from 'node:path'
import { createRequire } from 'node:module'
const { defineConfig, devices } = createRequire(resolve(process.cwd(), 'package.json'))('@playwright/test')
const repoRoot = resolve(process.cwd(), '..')
const qaRoot = resolve(repoRoot, '.local/qa/frontend-a-repair1')
export default defineConfig({
  testDir: resolve(qaRoot, 'harness'),
  testMatch: 'frontend-a-regressions.spec.ts',
  outputDir: resolve(qaRoot, 'regression-results'),
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  use: { ...devices['Desktop Chrome'], headless: true, baseURL: 'http://127.0.0.1:5175', trace: 'retain-on-failure' },
  webServer: { command: 'npm run dev -- --host 127.0.0.1 --port 5175', cwd: process.cwd(), url: 'http://127.0.0.1:5175', reuseExistingServer: false, timeout: 30_000 },
})
