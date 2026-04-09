// @ts-check
const { defineConfig, devices } = require('@playwright/test');
const os = require('os');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '..');
process.env.E2E_FRONTEND_BASE_URL ||= 'http://127.0.0.1:33002';
process.env.E2E_BACKEND_BASE_URL ||= 'http://127.0.0.1:38002';
process.env.E2E_TEST_DB_PATH ||= path.join(REPO_ROOT, 'data', 'e2e', 'doc_auth.db');

const FRONTEND_BASE_URL = process.env.E2E_FRONTEND_BASE_URL;
const BACKEND_BASE_URL = process.env.E2E_BACKEND_BASE_URL;
const TEST_DB_PATH = process.env.E2E_TEST_DB_PATH;
const FRONTEND_PORT = new URL(FRONTEND_BASE_URL).port || '33002';
const BACKEND_PORT = new URL(BACKEND_BASE_URL).port || '38002';
const FRONTEND_ORIGIN = new URL(FRONTEND_BASE_URL).origin;
const CORS_ORIGINS = JSON.stringify([
  ...new Set([
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:3001',
    'http://127.0.0.1:3001',
    FRONTEND_ORIGIN,
  ]),
]);
const BACKEND_HEALTH_URL = new URL('/health', `${BACKEND_BASE_URL.replace(/\/+$/, '')}/`).toString();
const OUTPUT_DIR = process.env.E2E_OUTPUT_DIR || path.join(os.tmpdir(), 'ragflowauth_playwright_docs_nosetup');

module.exports = defineConfig({
  testDir: './e2e/tests',
  testMatch: ['**/docs.notification-settings.spec.js'],
  outputDir: OUTPUT_DIR,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    baseURL: FRONTEND_BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  webServer: [
    {
      command: 'python -m backend',
      cwd: REPO_ROOT,
      url: BACKEND_HEALTH_URL,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        ...process.env,
        DATABASE_PATH: TEST_DB_PATH,
        E2E_TEST_DB_PATH: TEST_DB_PATH,
        PORT: BACKEND_PORT,
        CORS_ORIGINS,
      },
    },
    {
      command: 'npm run start',
      cwd: __dirname,
      url: FRONTEND_BASE_URL,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        ...process.env,
        BROWSER: 'none',
        PORT: FRONTEND_PORT,
        REACT_APP_AUTH_URL: BACKEND_BASE_URL,
      },
    },
  ],
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
