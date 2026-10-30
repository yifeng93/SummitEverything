import { resolve } from 'node:path'
import { randomUUID } from 'node:crypto'
import { defineConfig, devices } from '@playwright/test'

const repo = resolve(process.cwd())
const qaRoot = resolve(repo, '.local/qa/external-watch-20261030')
const sessionToken = `external-watch-qa-${randomUUID()}`
const apiPort = 6185
const webPort = 8895

export default defineConfig({
  testDir: qaRoot,
  testMatch: 'external-watch.spec.ts',
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  outputDir: resolve(qaRoot, 'playwright-output'),
  use: {
    ...devices['Desktop Chrome'],
    headless: true,
    baseURL: `http://127.0.0.1:${webPort}`,
    trace: 'on',
    screenshot: 'on',
    video: 'retain-on-failure',
  },
  webServer: [
    {
      command: `PYTHONPATH=${resolve(repo, 'src')}:${qaRoot} ${resolve(repo, '.venv/bin/python')} -m uvicorn fixture_app:create_app --factory --host 127.0.0.1 --port ${apiPort}`,
      cwd: qaRoot,
      url: `http://127.0.0.1:${apiPort}/api/v1/health`,
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        QA_PROFILE_ROOT: resolve(qaRoot, `profile-${sessionToken}`),
        QA_EVIDENCE_DIR: resolve(qaRoot, 'logs'),
        QA_LOCAL_MODEL_DIR: '/Users/hanwenbo/ai/SummitEverything/.local/qa/local-retrieval-probe/models/46fbe35fd4374a00fee7de77dfddaeb6dd6a2c59',
        QA_SESSION_TOKEN: sessionToken,
        QA_API_PORT: String(apiPort),
        QA_WEB_PORT: String(webPort),
        SUMMIT_OFFLINE_GUARD_ACTIVE: '1',
      },
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${webPort}`,
      cwd: resolve(repo, 'web'),
      url: `http://127.0.0.1:${webPort}`,
      reuseExistingServer: false,
      timeout: 60_000,
      env: { SUMMIT_API_TARGET: `http://127.0.0.1:${apiPort}`, SUMMIT_SESSION_TOKEN: sessionToken },
    },
  ],
})
