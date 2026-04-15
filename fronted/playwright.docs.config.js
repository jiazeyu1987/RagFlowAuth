// @ts-check
const { defineConfig, devices } = require('@playwright/test');
const os = require('os');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '..');
process.env.E2E_FRONTEND_BASE_URL ||= 'http://127.0.0.1:33002';
process.env.E2E_BACKEND_BASE_URL ||= 'http://127.0.0.1:38002';
process.env.E2E_TEST_DB_PATH ||= path.join(REPO_ROOT, 'data', 'e2e', 'doc_auth.db');
process.env.E2E_BOOTSTRAP_SCRIPT ||= path.join(REPO_ROOT, 'scripts', 'bootstrap_doc_test_env.py');
process.env.E2E_BOOTSTRAP_REQUIRE_RAGFLOW ||= '1';
process.env.E2E_JWT_SECRET_KEY ||= 'ragflowauth-doc-e2e-jwt-secret';

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
const OUTPUT_DIR = process.env.E2E_OUTPUT_DIR || path.join(os.tmpdir(), 'ragflowauth_playwright_docs');
const JWT_SECRET_KEY = process.env.E2E_JWT_SECRET_KEY;

module.exports = defineConfig({
  testDir: './e2e/tests',
  testMatch: ['**/docs*.spec.js'],
  outputDir: OUTPUT_DIR,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [['html', { open: 'never' }], ['list']],
  globalSetup: require.resolve('./e2e/global-setup'),
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
        JWT_SECRET_KEY,
        DOCUMENT_CONTROL_SCHEDULER_INTERVAL_SECONDS: '5',
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
