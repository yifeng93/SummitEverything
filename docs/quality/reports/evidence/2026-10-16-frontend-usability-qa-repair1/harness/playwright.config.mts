import { resolve } from 'node:path'
import { defineConfig } from '@playwright/test'
const here = new URL('.', import.meta.url).pathname
export default defineConfig({
  testDir: resolve(here), testMatch: 'viewport-qa.spec.ts', fullyParallel: false, workers: 1, reporter: 'list',
  use: { headless: true, baseURL: 'http://127.0.0.1:5191', trace: 'retain-on-failure' },
  webServer: { command: 'npm run dev -- --host 127.0.0.1 --port 5191', cwd: resolve(here, '../../../../web'), url: 'http://127.0.0.1:5191', reuseExistingServer: false, timeout: 30000 },
})
