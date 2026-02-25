// @ts-check
const { defineConfig, devices } = require('@playwright/test');
const os = require('os');
const path = require('path');

const FRONTEND_BASE_URL = process.env.E2E_FRONTEND_BASE_URL || 'http://localhost:3000';
// Some Windows environments deny deleting files under the repo workspace (e.g. `test-results/.last-run.json`),
// which breaks Playwright. Default to an OS temp output dir to keep E2E runnable everywhere.
const OUTPUT_DIR = process.env.E2E_OUTPUT_DIR || path.join(os.tmpdir(), 'ragflowauth_playwright');

module.exports = defineConfig({
  testDir: './e2e/tests',
  outputDir: OUTPUT_DIR,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    baseURL: FRONTEND_BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  globalSetup: require.resolve('./e2e/global-setup'),
  webServer: {
    command: 'npm run start',
    url: FRONTEND_BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      BROWSER: 'none',
    },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
