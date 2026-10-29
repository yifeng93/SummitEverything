const { defineConfig, devices } = require('../../web/node_modules/@playwright/test')
const path = require('node:path')
module.exports = defineConfig({
  testDir: __dirname,
  testMatch: 'ask-browser.spec.cjs',
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  outputDir: path.join(__dirname, 'playwright-results'),
  use: { ...devices['Desktop Chrome'], headless: true, baseURL: 'http://127.0.0.1:5174' },
  webServer: { command: 'npm run dev -- --host 127.0.0.1 --port 5174', cwd: path.resolve(__dirname, '../../web'), url: 'http://127.0.0.1:5174', reuseExistingServer: false, timeout: 30000 },
})
